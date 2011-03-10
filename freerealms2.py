# -*- coding: utf-8 -*-
from datetime import date

#from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app

import web


# TODO: User box as widget... how to?

class FreeRealmsApplication(web.Application):

    def get_root(self):
        return MainPage()

class UserWidget(web.List):

    def __init__(self, page):
        super(UserWidget, self).__init__()
        if page.user:
            self.append(web.Text('Welcome, %s!' % page.user.nickname()))
            self.append(page.logout_link(u'Logout'))
        else:
            self.append(web.Text('You are currently not logged in.'))
            self.append(page.login_link(u'Login'))

class FreeRealmsPage(web.Page):

    title = u'Free Realms'

    def content(self):
        while False:
            yield

    def header(self):
        header = web.DivPanel()
        header.append(web.Heading(self.title))
        header.append(UserWidget(self))
        return header

    def footer(self):
        year = date.today().year
        footer = web.Paragraph()
        email = web.Email('marc@nieper-wisskirchen.de', subject='Free Realms',
                          content=u'Marc Nieper-Wißkirchen')
        footer.append(u'Copyright © 2011–%d ' % year, email)
        return footer

    def update(self):
        body = self.body
        body.append(self.header())
        for block in self.content():
            body.append(block)
        body.append(self.footer())


class MainPage(FreeRealmsPage):

    def welcome_article(self):
        article = web.Section(u'Welcome to the Free Realms')
        article.append(web.Paragraph(u'The Free Realms is a site dedicated to '
                                      'play-by-post role-playing games.'))
        section = web.SubSection(u'Create your own campaign')
        paragraph = web.Paragraph()
        paragraph.append(u'In the Free Realms you can easily create '
                          'your own campaign. Just follow the link '
                          'below. ',
                         u'(Note that you will need to log in with a ',
                         web.Link('https://www.google.com/accounts/',
                                  u'Google Account'), u' first.)')
        section.append(paragraph)
        article.append(section)
        return article
                       
    def content(self):
        yield self.welcome_article()

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


wsgi_app = FreeRealmsApplication.wsgi_app(debug=True)


def main():
    run_wsgi_app(wsgi_app)


if __name__ == "__main__":
    main()
