from google.appengine.ext.webapp.util import run_wsgi_app

import web2 as web

application = web.Application()

class MainPage(web.HTMLPage):

    def title(self):
        return u'Free Realms'

    def setup(self):
        super(MainPage, self).setup()
        self.body.append(web.Heading(u'Free Realms'))


@application.handler('/')
class MainController(web.PageController):

    def view(self):
        return MainPage(self)


wsgi_app = application.wsgi_app(debug=True)


def main():
    run_wsgi_app(wsgi_app)


if __name__ == "__main__":
    main()


