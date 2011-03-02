from google.appengine.ext import webapp

# XXX This is what a controller will look like
class Controller(object):


    def etag(self):
        pass


    def render(self):
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

class Application(object):

    def __init__(self, controller):
        self.controller = controller
        self._url_mapping = [('/', self._request_handler_factory())]
        self._actions = []

    def _request_handler_factory(action=None):
        request_handler = type('RequestHandler', (_RequestHandler,), {
            'controller' : self._controller,
            'actions' : self._actions,
            'action' : action })
        return request_handler

    def add_action(self, action):
        self._actions.append(action)
   
    def add_route(self, url_path, action):
        self._routes.append((url_path, self._request_handler_factory(action)))

    def wsgi_app(debug=False):
        return webapp.WSGIApplication(self.url_mapping, debug)
