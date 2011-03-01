class StopHandler(Exception):
    pass


class Controller(self):

    def __init__(self, requestHandler):
        self._requestHandler = requestHandler

    def get_component(self, name):
        return self._requestHandler.components[name]

    def return_if_match(self, etag):
        if etag in self._requestHandler.request.if_none_match:
            self._requestHandler.error(304)
            raise StopHandler()

    def _redirect(self, url):
        self._requestHandler.response.error(303)
        self._requestHandler.response.headers['Location'] = url
        raise StopHandler()

    def bad_request(self):
        self._requestHandler.response.error(400)
        raise StopHandler()

    def url(self, page=None, **kwargs):
        if not page:
            page = self._page
        query = {}
        for name, component in sorted(self._requestHandler.components):
            for key, value in sorted(component.query()):
                if value:
                    query['%s_%s' % (name, key)] = value
        query.update(kwargs)
        query_string = urllib.urlencode(query, doseq=True)
        url = '%s?%s' % (page.url_path(), query_string)
        return self._requestHandler.request.relative_url(url,
                                                         to_application=self)

    def goto(self, page=None, **kwargs):
        self._redirect(self.url(page, **kwargs))

    def login(self):
        self._redirect(users.create_login_url(self._requestHandler.request.uri))

    def show(self, output):
        self._requestHandler.response.out.write(output)
        raise StopHandler()


class RequestHandler(webapp.RequestHandler):

    def __init__(self, application, page):
        self.components = {}
        self.controller = Controller(self)

    def get(self, *args):
        self.page = self.page_factory(*args)
        self.initialize_components()
        try:
            self.page.render(controller)
        except StopHandler():
            pass
        
    def post(self, *args):
        self.page = self.page_factory(*args)
        self.initialize_components()
        try:
            self.page.action_handler(controller)
            self.page.render(controller)
        except StopHandler():
            pass

    def initialize_components(self):
        arguments = self._request.arguments()
        for name, component_factory in self.application.components:
            query = {}
            for argument in arguments:
                prefix, sep, key = argument.partition('_')
                if sep == '_' and prefix == name:
                    query[key] = self.request.get_all(argument)
            self.components[name] = component_factory(query)


class Page(object):

    def __init__(self, *args):
        pass

    def action_handler(self, controller):
        pass

    def render(self, controller):
        pass


class Application(object):

    def __init__(self):
        self.components = {}

    def component(self, name):
        def decorator(component):
            self.component[name] = component
        return decorator

    def page(self, url):
        # TODO
        pass

    def wsgi_app(self, debug=False):
        # TODO
        pass

