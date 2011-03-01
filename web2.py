from contextlib import contextmanager
import cgi

from google.appengine.api import users
from google.appengine.ext import webapp


class StopHandler(Exception):
    pass


class PageController(object):

    def __init__(self, *args):
        pass

    def url_path(self):
        return self._url_pattern

    def initialize(self, requestHandler):
        self._requestHandler = requestHandler        

    def get_component(self, name):
        return self._requestHandler.components[name]

    def etag(self):
        return None

    def _redirect(self, url):
        self._requestHandler.response.error(303)
        self._requestHandler.response.headers['Location'] = url
        raise StopHandler()

    def bad_request(self):
        self._requestHandler.response.error(400)
        raise StopHandler()

    def url(self, controller=None, **kwargs):
        if not controller:
            controller = self
        query = []
        for name, component in sorted(self._requestHandler.components.items()):
            for key, value in sorted(component.query().items()):
                if value:
                    query.append(('%s_%s' % (name, key), value))
        query.extend(sorted(kwargs.items()))
        query_string = urllib.urlencode(query, doseq=True)
        url = '%s?%s' % (controller.url_path(), query_string)
        return self._requestHandler.request.relative_url(url,
                                                         to_application=self)

    def goto(self, controller=None, **kwargs):
        self._redirect(self.url(controller, **kwargs))

    def login(self):
        self._redirect(users.create_login_url(self._requestHandler.request.uri))

    def view(self):
        return None

    def action_handler(self, controller):
        pass


class RequestHandler(webapp.RequestHandler):

    def __init__(self):
        self.components = {}

    def get(self, *args):
        self.controller = self.controller_factory(*args)
        self.controller.initialize(self)
        self.initialize_components()
        etag = self.controller.etag()
        if etag and etag in self.request.if_none_match:
            self.error(304)
            return
        self.controller.view().render(self.response.out)

    def post(self, *args):
        self.controller = self.controller_factory(*args)
        self.controller.initialize(self)
        self.initialize_components()
        try:
            pass
            # TODO actions
        except StopHandler():
            return
        self.controller.view().render(self.response.out)

    def initialize_components(self):
        arguments = self.request.arguments()
        for name, component_factory in self.application.components:
            query = {}
            for argument in arguments:
                prefix, sep, key = argument.partition('_')
                if sep == '_' and prefix == name:
                    query[key] = self.request.get_all(argument)
            self.components[name] = component_factory(query)


class PageView(object):

    def __init__(self, controller):
        self.controller = controller
        self.setup()

    def setup(self):
        pass

    def render(self, out):
        pass


class HTMLWriter(object):

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

    def starttag(self, name, empty=False):
        if empty:
            self.write('<%s />' % name)
        else:
            self.write('<%s>' % name)

    def endtag(self, name):
        self.write('</%s>' % name)

    @contextmanager
    def block(self, name):
        self.starttag(name)
        self.writeln()
        self.indent()
        yield
        if not self._newline:
            self.writeln()
        self.dedent()
        self.endtag(name)
        self.writeln()

    @contextmanager
    def inline(self, name):
        self.starttag(name)
        yield
        self.endtag(name)

class HTMLPage(PageView):

    def setup(self):
        super(HTMLPage, self).setup()
        self.body = Body()

    def title(self):
        return u''

    def doctype(self):
        return '<!doctype html>'

    def render(self, out):
        writer = HTMLWriter(out)
        writer.writeln(self.doctype())
        with writer.block('html'):
            with writer.block('head'):
                with writer.inline('title'):
                    writer.content(self.title())
            self.body.render(writer)


class Element(object):

    def render(self, writer):
        pass


class Heading(Element):

    def __init__(self, title, level=1):
        self._title = title
        self._level = level

    def render(self, writer):
        with writer.inline('h%d' % self._level):
            writer.content(self._title)


class Compound(Element):

    def __init__(self):
        self._children = []

    def append(self, element):
        self._children.append(element)

    def render(self, writer):
        for child in self._children:
            child.render(writer)


class Body(Compound):

    def render(self, writer):
        with writer.block('body'):
            super(Body, self).render(writer)


class Application(object):

    def __init__(self):
        self.components = {}
        self.url_mapping = []

    def component(self, name):
        def decorator(componentClass):
            self.component[name] = componentClass
            return componentClass
        return decorator

    def handler(self, url_pattern):
        def decorator(controllerClass):
            controllerClass._url_pattern = url_pattern
            requestHandlerClass = type('RequestHandler', (RequestHandler,), {
                'application' : self, 'controller_factory' : controllerClass})
            self.url_mapping.append((url_pattern, requestHandlerClass))
            return controllerClass
        return decorator
    
    def wsgi_app(self, debug=False):
        return webapp.WSGIApplication(self.url_mapping, debug)    
