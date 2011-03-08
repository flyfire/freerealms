from google.appengine.ext import webapp


# TODO subpages <-> actions <-> states <-> properties als Decorators!


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


class Property(object):

    def __init__(self, data):
        if isinstance(data, Property):
            self.initialize_from_property(data)
        self.initialize_from_encoded(data)

    def initialize_from_property(data):
        pass

    def initialize_from_encoded(data):
        pass

    def __get__(self):
        return None

    def encoded(self):
        return u''
    

class IntProperty(Property):

    def initialize_from_property
        


class State(object):

    pass


class Application(object):

    properties = {}  # instance of state --> properties!

    @classmethod
    def wsgi_app(cls, debug=False):
        request_handler = type('RequestHandler', (_RequestHandler,), {
            'application' : cls })
        return webapp.WSGIApplication([(r'/(.*)', request_handler)], debug)

    def _initialize_from_dict(self, data):
        for name, prop in self.properties.items():
            self.instances[name] = factory(data.get(data))

    def _initialize_from_app(self, app):
        for name, factory in state.items():
            self.instances[name] = factory(app.instances.get(name))

    def _query_string(self):
        query = [(name, instance.encoded())
                 for name, instance in sorted(self.instances.items())]
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


class Page(object):

    subpages = {}
    parameters = ()
    
    def initialize(self, application):
        self.application = application 

    def get(self, key):
        page = self.subpages.get(key)
        if not page:
            return None
        return page(self)

    def etag(self):
        return None

    def render(self, out):
        return
