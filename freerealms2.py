from google.appengine.ext.webapp.util import run_wsgi_app

import web

class MyPage(web.Page):

    def render(self, out):
        out.write('<!doctype html>\n')

    def info_page(self):
        return InfoPage()

    subpages = {'info': info_page}


class InfoPage(web.Page):

    def render(self, out):
        out.write('info')


class MyApplication(web.Application):

    def get_root(self):
        return MyPage()


wsgi_app = MyApplication.wsgi_app(debug=True)


def main():
    run_wsgi_app(wsgi_app)


if __name__ == "__main__":
    main()


