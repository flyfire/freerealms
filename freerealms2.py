from google.appengine.ext.webapp.util import run_wsgi_app

import web

class MyPage(web.Page):

    count = web.IntProperty('count')

    def initialize(self):
        self.error = u''

    def get_document(self):
        document = web.Document('Main Page')
        heading = web.Heading('Welcome!', level=1)
        document.body.append(heading)
        document.body.append(web.Paragraph(web.Text(self.error)))
        document.body.append(web.Paragraph(
            web.Text('Count is %d.' % self.count)))
        document.body.append(web.Paragraph(self.info_link('click me!')))
        document.body.append(web.Paragraph(self.count_link('COUNT!')))
        form = self.action()
        document.body.append(form)
        return document

    @web.link
    def count_link(self, application):
        page = self.copy()
        page.count += 1
        return page

    @web.link
    def info_link(self, application):
        application.x = 3
        page = self.get('info')
        page.y = 12
        return page

    @web.subpage('info')
    def info_page(self, key):
        return InfoPage(self, key)

    @web.action('handler', web.StringProperty('name'))
    def action(self, name):
        if not name:
            self.error = u'Text missing!!!'
            return

class InfoPage(web.Page):

    y = web.IntProperty('y')

    def get_document(self):
        document = web.Document('Info Page')
        return document


class MyApplication(web.Application):

    x = web.IntProperty('x')

    def get_root(self):
        return MyPage()


wsgi_app = MyApplication.wsgi_app(debug=True)


def main():
    run_wsgi_app(wsgi_app)


if __name__ == "__main__":
    main()


