# -*- coding: utf-8 -*-
from google.appengine.ext import webapp

class TestComponent(Component):

    z = IntProperty()
    y = IntProperty()

    x = IntProperty()
    
    z = Property("action", int, default)

    @action("add", "x", "y", "z")
    def add(x, y, z):
        pass



class Property(object):

    def __init__(self, type_, default=None):
        self._type = type_
        self._default = default

    def __get__(self, instance, owner):
        if not instance:
            return self
        properties = getattr(instance, '_properties', None)
        if properties:
            

    def __set__(self, instance, value):
        instance
    
    def _decode(self, variable, query, suffix=u''):
        

class ComponentClass(type):
    """Metaclass for Component classes"""

    pass


class Component(object):
    """A web component"""
    
    __metaclass__ = ComponentClass

    def _initialize(self, request)
        for argument in request.arguments():
            if len(argument) > 1 and argument[0] == u'_':
                self._set(argument[1], request.get_all(argument))

    def _set(key, query):
        name, sep, suffix = key.partition(u'_')
        prop = getattr(self.__class__, name, None)
        if isinstance(prop, Property):
            prop._decode(getattr(self, name), query, suffix)

class MyComponent(object):

    counter = Property(int, 0)
    sub_component = ComponentProperty()


# ------> Eine Form löst eine Aktion aus. An dieser sind Parameter gebunden;

    @action
    def inc(self, **kwargs):
        pass


    def inc(self, **kwargs):

        pass


class _RequestHandler(webapp.RequestHandler):

    def get(self, *args):
        if not self.action:
            self.update_action()
            args = self.get_arguments()
        state = self.get_state()
        if self.action:
            self.do_action()
            return
        # TODO check etag (self.controller.etag)
        self.controller.render(state, self.response.out) # TODO AttributeError

    def do_action(self):
        actions[self.action](state, *args)
        query = self.get_query(state)
        self.error(303)
        self.reponse.headers['Location'] = (
            self.request.relative_url('/?%s' % query, to_application=True))

    def post(self, *args):
        self.update_action()
        if not self.action:
            self.error(400)
            return
        args = self.get_arguments()
        state = self.get_state()
        self.do_action()
            
    def get_state(self):
        # TODO
        return None

    def get_arguments(self):
        # TODO
        return []

    def get_query(self, state):
        # TODO              
        return ''

    def update_action(self):
        self.action = self.request.get_range('action', 0, len(self.actions) - 1,
                                             None)



class RequestHandler(webapp.RequestHandler):


    def get(*args):
        state = self.application.component()

        for argument in self.request.arguments():
            while True:
                prefix, sep, suffix = argument.partition(u'_')
                

        state._initialize(self.request)
        app = self.application()
        app.initialize(state)
        etag = app.etag()
        if etag:
            pass # TODO
        app.render(self.response.out)

    def post(*args):
        # TODO handle action
        pass

    def action(state):
        pass

    ?action=3&param1=...&param2=...

    _keyword=...&_y=...&_z=...&_t=555&x_y=3&...&_=goto_field&param1=...&param2=...&param3=...

class Application(object):

    def initialize(self, state):
        self.state = state

    def etag(self):
        return None

    def render(self, out):
        pass


class MyApplication(object):

    component = MyComponent

    def etag(self, component):
        return None

    def render(self, component):
        return u'<!doctype html>'


def request_handler(application):
    return type('RequestHandler', (RequestHandler,), {
        'application' : application})


def wsgi_app(application, debug=False):
    return webapp.WSGIApplication(('/', request_handler(application)), debug)
