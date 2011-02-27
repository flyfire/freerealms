import google.appengine.ext.webapp

class AppState(object):

    def __init__(self, app_state):
        pass
        
    def query_string(self):
        return ???


class Page(object):

    def __init__(self, state, *args):
        pass

    def initialize(self, request):
        state = {}
        for prop in cls.properties:
            values = request.get_all(prop.key)
            state[prop.key] = prop(values)
                

    def isProtected(self):
        return False

    @classmethod
    def query_string(cls, state):
        query = {}
        for prop in cls.properties: # TODO
            value = state.get(prop)
            if value and value != prop.default: # TODO
                query[prop.key] = unicode(value).encode('utf-8')
        return urllib.urlencode(query, doseq=True)

    @classmethod
    def url(cls, state, *args):
        return '%s?%s' % (cls.url_path(*args), cls.url(state))        

    @classmethod
    def url_path(cls, *args):
        raise NotImplemented

    @classmethod
    def requestHandler(cls):
        return type("PageRequestHandler", (PageRequestHandler,), 
            {'page_factory': cls})

    @classmethod
    def url_mapping(cls):
        return cls.url_path, cls.requestHandler
    
        
        
    
    # TODO index
    def generate_key_values(self):
        return ()

    def update(self):
        pass
    
    def render(self, response):
        raise NotImplemented


class PageRequestHandler(webapp.RequestHandler):

    def get(self, *args):
    
        pass
        
    def post(self, *args):
        
        pass


class Property(object):
    def __init__(self, factory, default):
        self._factory = factory
        self._default = default

    def __call__(self, values)
        if not values:
            state[prop.key] = prop._default
        elif len(values) = 1:
            try:
                state[prop.key] = prop._factory(values[0])
            except ValueError:
                state[prop.key] = prop._default
        else:
            try:
                state[prop.key] = prop._factory(values)
            except ValueError:
                state[prop.key] = prop._default
                            
#---------------------------------#

class MainPage(Page):

    describe = Property(str, '')

    @classmethod
    def url_path(cls, *args):
        return '/'

    @index('Counter')
    def counter(self):
        return # XXX

    @action(form_data) # XXX
    def add(self):
        

