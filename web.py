from copy import copy
import functools
import urllib
from xml.etree import ElementTree

from google.appengine.ext import webapp

# TODO url builder
# TODO actions <-> als Decorators!
# TODO response: relative_url for _url

class _NotFoundException(Exception):
    pass


class _RequestHandler(webapp.RequestHandler):

    def get(self, path):
        app = self.application(self.request)
        try:
            page = app._get_page(path)
        except _NotFoundException:
            self.error(404)
            return
        app._initialize_page(page, self.request)
        etag = page.etag()
        if etag:
            h = hashlib.sha1()
            h.update(repr(etag))
            hexdigest = h.hexdigest()
            self.response.headers['ETag'] = '"%s"' % hexdigest
            if hexdigest in self.request.if_none_match:
                self.error(304)
                return
        page._render(self.response.out)

    def post(self, path):
        app = self.application(self.request)
        path, sep, action_key = path.rpartition('/')
        if not action:
            self.error(405)
            return
        try:
            page = app._get_page(path)
        except _NotFoundException:
            self.error(404)
            return
        app._initialize_page(page, self.request)
        handler = page._actions.get(action)
        if not handler:
            self.error(405)
            return
        # TODO update form data!!!
        # TODO
        args = []
        for prop in handler.property:
            args.append(prop.decode(self.request.get(prop.key)))
        redirection = handler(page, *args) # TODO
        if redirection:
            self.error(303)
            self.response.headers['Location'] = redirection
            return
        page._render(self.response.out)


class _SubPage(object):

    def __init__(self, key, func):
        self.key = key
        self.func = func
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


class _Action(object):

    def __init__(self, key, func, *properties):
        self.key = key
        self.func = func
        self.properties = properties

    def __get__(self, instance, owner):
        if not instance:
            return self
        @functools.wraps(self.func)
        def wrapper():
            app = instance.application
            url = app._url(instance, action=self.key)
            return Form(url)
        return wrapper

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


def subpage(key):
    def decorator(func):
        return functools.update_wrapper(_SubPage(key, func), func)
    return decorator

def action(key, *properties):
    def decorator(func):
        return functools.update_wrapper(_Action(key, func, *properties), func)
    return decorator

def link(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        app = copy(self.application)
        page = func(self, app, **kwargs)
        return Link(app._url(page), *args)
    return wrapper


class Property(object):

    def __init__(self, key):
        self.key = key

    def __get__(self, instance, owner):
        if not instance:
            return self
        try:
            return instance._property_values[self.key]
        except (KeyError, AttributeError):
            return self.decode(u'')

    def __set__(self, instance, value):
        try:
            values = instance._property_values
        except AttributeError:
            values = instance._property_values = {}
        values[self.key] = value

    def decode(self, string):
        return None

    def encode(self, value):
        return u''


class IntProperty(Property):

    def decode(self, string):
        try:
            return int(string)
        except ValueError:
            return 0
            
    def encode(self, value):
        if value:
            return str(value)
        else:
            return u''

class StringProperty(Property):

    def decode(self, string):
        return string

    def encode(self, value):
        return value

class _Propertied(type):
    
    def __init__(cls, name, bases, dct):
        super(_Propertied, cls).__init__(name, bases, dct)
        cls._properties = {}
        for base in bases:
            if isinstance(base, _Propertied):
                cls._properties.update(base._properties)
        for name, value in dct.items():
            if isinstance(value, Property):
                cls._properties[value.key] = value


class Application(object):

    __metaclass__ = _Propertied

    def __init__(self, request):
        for key, prop in self._properties.items():
            prop.__set__(self, prop.decode(request.get(key)))

    @classmethod
    def wsgi_app(cls, debug=False):
        request_handler = type('RequestHandler', (_RequestHandler,), {
            'application' : cls })
        return webapp.WSGIApplication([(r'/(.*)', request_handler)], debug)

    def _url(self, page, action=u''):
        prefix = self._get_path(page)
        path = prefix + ('/' if prefix != '/' and action else '') + action
        query_string = self._query_string(page)
        # XXX Use relative_url from webob.
        return '%s?%s' % (path, query_string) if query_string else '/' + path

    def _initialize_page(self, page, request):
        page.application = self
        for key, prop in page._properties.items():
            prop.__set__(page, prop.decode(request.get(key)))
        page.initialize()

    def _query_string(self, page=None):
        app_props = [
            (name, encoded) for name, encoded in (
                (name, prop.encode(prop.__get__(self, self.__class__)))
                for name, prop in self._properties.items())
            if encoded]
        page_props = [
            (name, encoded) for name, encoded in (
                (name, prop.encode(prop.__get__(page, page.__class__)))
                for name, prop in page._properties.items())
            if encoded] if page else []
        return urllib.urlencode(sorted(app_props + page_props))
            
    def get_root(self):
        return None

    def _get_page(self, path):
        segments = path.split('/')
        page = self.get_root()
        if not page:
            raise _NotFoundException()
        for segment in path.split('/'):
            if not segment:
                continue
            page = page.get(segment)
            if not page:
                raise _NotFoundException()
        return page
        
    def _get_path(self, page):
        path = ''
        while page._parent:
            path = '/' + page._key + path
            page = page._parent
        path = path or '/'
        return path


class _PageMeta(_Propertied):

    def __init__(cls, name, bases, dct):
        super(_PageMeta, cls).__init__(name, bases, dct)
        cls._subpages = {}
        cls._actions = {}
        for base in bases:
            if isinstance(base, _PageMeta):
                cls._subpages.update(base._subpages)
                cls._actions.update(base._actions)
        for name, value in dct.items():
            if isinstance(value, _SubPage):
                cls._subpages[value.key] = value.func
            if isinstance(value, _Action):
                cls._actions[value.key] = value


class Page(object):

    __metaclass__ = _PageMeta

    def __init__(self, parent=None, key=''):
        self._parent = parent
        self._key = key

    def initialize(self):
        return

    def _url(self, page):
        return self.application._url(page)

    def get(self, key):
        page = self._subpages.get(key)
        if not page:
            return None
        return page(self, key)

    def copy(self):
        return copy(self)

    def etag(self):
        return None

    def _render(self, out):
        tb = ElementTree.TreeBuilder()
        self.get_document().render(tb)
        document = tb.close()
        tree = ElementTree.ElementTree(document)
        out.write('<!doctype html>\n')
        tree.write(out, encoding='utf-8')

    def get_document(self):
        return Document()


class Element(object):

    def render(self, tb):
        return

class InlineElement(Element):

    pass


class Document(Element):

    def __init__(self, title=u''):
        self.title = title
        self.body = []

    def render(self, tb):
        tb.start('html', {})
        tb.start('head', {})
        tb.start('title', {})
        tb.data(self.title)
        tb.end('title')
        tb.end('head')
        tb.start('body', {})
        for element in self.body:
            element.render(tb)
        tb.end('body')
        tb.end('html')


class Inline(Element):

    def __init__(self, *args):
        self._elements = []
        for arg in args:
            self.append(arg)

    def append(self, data):
        if isinstance(data, basestring):
            self._elements.append(Text(data))
        elif isinstance(data, InlineElement):
            self._elements.append(data)
        else:
            raise TypeError

    def render(self, tb):
        for element in self._elements:
            element.render(tb)

class Heading(Inline):

    def __init__(self, *args, **kwargs):
        super(Heading, self).__init__(*args)
        self._level = kwargs.get('level', 1)

    def render(self, tb):
        tag = 'h%d' % self._level
        tb.start(tag, {})
        super(Heading, self).render(tb)
        tb.end(tag)


class Link(Inline, InlineElement):

    def __init__(self, href, *args):
        super(Link, self).__init__(*args)
        self._href = href
        
    def render(self, tb):
        tb.start('a', { 'href' : self._href })
        super(Link, self).render(tb)
        tb.end('a')


class Text(InlineElement):

    def __init__(self, text):
        self._text = text

    def render(self, tb):
        tb.data(self._text)

class Form(Element):

    def __init__(self, action):
        self._action = action
        self._body = []

    def append(self, child):
        self._body.append(child)

    def render(self, tb):
        tb.start('form', { 'method' : 'post', 'action' : self._action })
        for element in self._body:
            element.render(tb)
        tb.end('form')

class TextInput(InlineElement):

    def __init__(self, value=u''):
        self._value = value
    
    def render(self, tb):
        tb.start('input', { 'type' : 'text' })
        tb.end('input')

class Submit(InlineElement):

    def __init__(self, value=u''):
        self._value = value
    
    def render(self, tb):
        tb.start('input', { 'type' : 'submit' })
        tb.end('input')

class Paragraph(Inline):

    def __init__(self, *args):
        super(Paragraph, self).__init__(*args)

    def render(self, tb):
        tb.start('p', {})
        super(Paragraph, self).render(tb)
        tb.end('p')
