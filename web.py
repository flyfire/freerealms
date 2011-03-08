import functools
import xml.sax.saxutils

from google.appengine.ext import webapp


# TODO subpages <-> actions <-> states <-> properties als Decorators!
# response: relative_url for _url
# howto tag
# http://stackoverflow.com/questions/1980380/how-to-render-a-doctype-with-pythons-xml-dom-minidom

class _NotFoundException(Exception):
    pass


class _RequestHandler(webapp.RequestHandler):

    def get(self, path):
        app = self.application()
        try:
            page = app._get_page(path)
        except _NotFoundException:
            self.error(404)
            return
        app._initialize_from_dict(self.request)
        page.initialize(app)
        etag = page.etag()
        if etag:
            h = hashlib.sha1()
            h.update(repr(etag))
            hexdigest = h.hexdigest()
            self.response.headers['ETag'] = '"%s"' % hexdigest
            if hexdigest in self.request.if_none_match:
                self.error(304)
                return
        page.render(self.response.out)

    def post(self, path):
        app = self.application()
        path, sep, action = path.rpartition('/')
        if not action:
            self.error(405)
            return
        try:
            page = app._get_page(path + sep)
        except _NotFoundException:
            self.error(404)
            return
        handler = page.actions.get(action)
        if not handler:
            self.error(405)
            return
        # TODO update form data!!!
        redirection = handler(page)
        if redirection:
            self.error(303)
            self.response.headers['Location'] = redirection
            return
        page.render(self.response.out)


class _SubPage(object):

    def __init__(self, key, func):
        self.key = key
        self.func = func
    
    def __call__(self, *args, **kwargs):
        return self.func(args, kwargs)


def subpage(key):
    def decorator(func):
        return functools.update_wrapper(_SubPage(key, func), func)
    return decorator


class Property(object):

    def __init__(self, key):
        self.key = key

    def __get__(self, instance, owner):
        if not instance:
            return self
        return instance._get_property_value(self.key)

    def __set__(self, instance, value):
        instance._set_property_value(self.key, value)

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
        else
            return u''


class _ApplicationMeta(type):

    def __init__(cls, name, bases, dct):
        super(_ApplicationMeta, cls).__init__(name, bases, dct)
        cls._properties = {}
        for base in bases:
            if isinstance(base, _ApplicationMeta):
                cls._properties.update(base._properties)
        for name, value in dct.items():
            if isinstance(value, Property):
                cls._properties[value.key] = value


class Application(object):

    __metaclass__ = _ApplicationMeta

    @classmethod
    def wsgi_app(cls, debug=False):
        request_handler = type('RequestHandler', (_RequestHandler,), {
            'application' : cls })
        return webapp.WSGIApplication([(r'/(.*)', request_handler)], debug)

    def _url(self, page):
        path = self._get_path(page)
        query_string = self._query_string
        return '%s?%s' % (path, query_string) if query_string else path

    def _get_property_value(self, key):
        try:
            return self._property_values[key]
        except AttributeError, KeyError:
            return self._properties[key].decode(u'')    

    def _set_property_value(self, key, value):
        try:
            values = self._property_values
        except AttributeError
            self._property_values = values = {}
        values[key] = value

    def _initialize_from_dict(self, data):
        for key, prop in self._properties.items():
            prop.__set__(self, prop.decode(data.get(key)))

    def _initialize_from_app(self, app):
        for key, prop in self._properties.items():
            try:
                prop.__set__(self, app._get_property_value(key))
            except KeyError:
                pass

    def _query_string(self):
        query = [(name, prop.encode(prop.__get__(self, self.__class__)))
                 for name, prop in sorted(self._properties.items())]
        return urllib.urlencode(query)
            
    def get_root(self):
        return None

    def _get_page(self, path):
        page = self.get_root()
        while True:
            if not page:
                raise _NotFoundException()
            if not path:
                return page
            segment, sep, path = path.partition('/')
            page = page.get(segment)

    def _get_path(self, page):
        path = ''
        while page._parent:
            path = page._key + '/' + path
            page = page._parent
        return path


class _PageMeta(type):

    def __init__(cls, name, bases, dct):
        super(_PageMeta, cls).__init__(name, bases, dct)
        cls._subpages = {}
        for base in bases:
            if isinstance(base, _PageMeta):
                cls._subpages.update(base._subpages)
        for name, value in dct.items():
            if isinstance(value, _SubPage):
                cls._subpages[value.key] = value.func


class Page(object):

    __metaclass__ = _PageMeta
    
    parameters = ()

    def __init__(self, parent=None, key=''):
        self._parent = parent
        self._key = key

    def initialize(self, application):
        self.application = application 

    def _url(self):
        return self.application._url(self)

    def get(self, key):
        page = self._subpages.get(key)
        if not page:
            return None
        return page(self, key)

    def etag(self):
        return None

    def get_html(self):
        return HTML()


class _Tag(object):

    def __init__(self, name, **attributes):
        self.name = name
        self.attributes = attributes

class _HTMLWriter(object):

    def __init__(self, out, indent=2, level=0):
        self._out = out
        self._level = level
        self._indent = indent
        self._newline = True

    def write(self, s):
        if self._newline:
            self._out.write(' ' * (self._indent * self._level))
            self._newline = False
        self._out.write(s)

    def writeln(self, s=u''):
        self.write('%s\n' % s)
        self._newline = True

    def indent(self):
        self._level += 1

    def dedent(self):
        self._level -= 1

    def content(self, s):
        self.write(cgi.escape(s))

    def emptytag(self, tag):
        self.starttag(self, tag, _empty=True)

    def starttag(self, tag, _empty=False):
        self.write('<%s' % tag.name)
        for attribute, value in tag.attributes:
            self.write(' %s=%s' % (attribute, saxutils.quoteattr(value))
        self.write(' />' if empty else '>')

    def endtag(self, tag):
        self.write('</%s>' % name)

    @contextmanager
    def block(self, tag):
        self.starttag(tag)
        self.writeln()
        self.indent()
        yield
        if not self._newline:
            self.writeln()
        self.dedent()
        self.endtag(tag)
        self.writeln()

    @contextmanager
    def inline(self, tag):
        self.starttag(tag)
        yield
        self.endtag(tag)


class HTML(object):

    def __init__(self):
        self.title = u''
        self.body = None

    def render(self, writer):
        writer.writeln('<!doctype html>')
        with writer.block(_Tag('html')):
            with writer.block(_Tag('head'))):
                with writer.inline(_Tag('title')):
                    writer.content(self.title.encode('utf-8'))
            with writer.block(_Tag('body')):
                if self.body:
                    self.body.render(writer)


class Element(object):
    pass

class Link(Element):

    def __init__(self, page):
        self._page = page
        self.content = None

    def render(self, writer):
        url = self._page._url()
        with writer.inline(_Tag('a', href=url)):
            if self.content:
                self.content.render(writer)

