import hashlib
import urllib

from google.appengine.api import users
from google.appengine.ext import webapp

import version


class ETag(object):
    version_hash = hashlib.sha1()
    version_hash.update('Version: %r\n' % (hex(version.HGVERSION),))

    def __init__(self):
        self._hash = self.version_hash.copy()
            
    def update(self, tag, s):
        self._hash.update('%s: %r\n' % (tag, s))
        
    def __str__(self):
        return self._hash.hexdigest()


class PageProperty(object):

    def __init__(self, factory, default):
        self._factory = factory
        self.default = default

    def decode(self, *strings):
        try:
            return self._factory(*strings)
        except AttributeError, TypeError:
            return self.default

    def encode(self, value):
        if value == self.default:
            return u''
        else:
            return unicode(value).encode('utf-8')


# TODO: change pagestate temporarily
class PageState(object):

    def __init__(self, model, request=None, **kwargs):
        self._model = model
        if request:
            #print model
            for name in model:
                setattr(self, name,
                        self._property(name).decode(*request.get_all(name)))
        for key, value in kwargs:
            setattr(self, key, value)
    
    def _property(self, name):
        return getattr(self._model, name)
        
    def __getattr__(self, name):
        return self.property(name).default

    def __str__(self):
        query = []
        for name in self._model:
            value = self._property(name).encode(getattr(self, name))
            if value:
                query.append((name, value))
        return urllib.urlencode(query, doseq=True)               


class PageModelClass(type):

    def __init__(cls, name, bases, dct):
        super(PageModelClass, cls).__init__(name, bases, dct)
        defined = set()
        for base in bases:
            try:
                defined.update(base._properties)
            except AttributeError:
                pass
        for key, value in dct.items():
            if isinstance(value, PageProperty):
                defined.add(key)
        cls._properties = sorted(defined)
            
    def __iter__(cls):
        return iter(cls._properties)


class PageModel(object):
    __metaclass__ = PageModelClass

    def __new__(cls, request=None, **kwargs):
        return PageState(cls, request, **kwargs)


class PageAction(object):
    def __init__(self, name, method):
        self.name = name
        self.method = method
    
    def __call__(self, page, instance, request):
        return self.method(page, instance, request)


def action(name):
    def decorator(method):
        return PageAction(name, method)
    return decorator


class PageClass(type):

    def __init__(cls, name, bases, dct):
        super(PageClass, cls).__init__(name, bases, dct)
        cls._actions = {}
        for base in bases:
            try:
                cls._actions.update(base._actions)
            except AttributeError:
                pass
        for key, value in dct.items():
            if isinstance(value, PageAction):
                cls._actions[key] = value

class Page(object):

    __metaclass__ = PageClass

    Model = PageModel
    
    def __init__(self, *args):
        pass

    def isProtected(self):
        return False

    def __call__(self, request):
        return self.Model(request)

    def actions(self):
        return self._actions.keys()

    def perform(self, action, instance, request):
        return self._actions[action](self, instance, request)

    def url(self, state):
        return '%s?%s' % (self.url_path(), state)

    def url_path(self):
        return self.url_pattern
        
    def absolute_url(self, state, request):
        return request.relative_url(self.url(state), to_application=True)

    @classmethod
    def requestHandler(cls):
        return type("PageRequestHandler", (PageRequestHandler,), 
            {'page_factory': cls})
    
    def generate_key_values(self):
        return ()

    def update(self, instance):
        pass
    
    def update_form_data(self, instance):
        pass
    
    def render(self, response):
        raise NotImplementedError


class PageRequestHandler(webapp.RequestHandler):

    def get(self, *args):      
        page = self.page_factory(*args)
        if page.isProtected() and not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
        instance = page(self.request)
        etag = ETag()
        for key, value in page.generate_key_values(instance):
            etag.update(key, value)
        etag_str = str(etag)
        self.response.headers['ETag'] = '"%s"' % (etag_str,)
        if etag_str in self.request.if_none_match:
            self.error(304)
            return
        page.update_form_data(instance, self.request)
        page.update(instance, self.request)
        page.render(instance, self.response)

    def post(self, *args):
        page = self.page_factory(*args)
        instance = page(self.request)
        for action in page.actions():
            if action in self.request.arguments():
                break
        else:
            self.error(405)
            return
        page.update_form_data(instance, self.request)
        redirection = page.perform(action, instance, self.request)
        if redirection:
            self.error(303)
            self.response.headers['Location'] = redirection
            return
        page.update(instance, self.request)
        page.render(instance, self.response)


class Application(object):

    def __init__(self):
        self.url_mapping = []

    def page(self, cls):
        self.url_mapping.append((cls.url_pattern, cls.requestHandler()))
        return cls

    def wsgi_app(self, debug=False):
        return webapp.WSGIApplication(self.url_mapping, debug)


application = Application()

