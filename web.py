from google.appengine.ext import webapp



class FreeRealmsApp(object):
    pass


@application(segment=r'/')
@needs(FreeRealmsApp)
class RootContext(object):

    def __init__(self):
        pass




def WSGIApplication(app):

    
    pass


class Application(object):

    def __init__(self):
        pass





class _RequestHandler(webapp.RequestHandler):

    def get(self, path):
        app = self.application()
        for context in app._contexts:
            # if context fits...
            pass
        
        app = self.application()
        context = app.get_root_context()
        for segment in path.split('/'):
            context = context[segment]
        # TODO etag
        context.render(self.response.out)
    pass


def WSGIApplication(application, debug=False):

    request_handler = type('RequestHandler', (_RequestHandler,), {
        'application' : application })
    return webapp.WSGIApplication((r'/(.*)', request_handler), debug)
