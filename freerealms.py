import hashlib
import os

from google.appengine.dist import use_library
use_library('django', '1.2')
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import counter # TODO implement several counters
import rest
import version

class CalculatedProperty(db.Property):
    data_type = None
    
    def __init__(self, verbose_name=None,
                 calc_func=(lambda model_instance: None), **kwds):
        super(CalculatedProperty, self).__init__(verbose_name, **kwds)
        self.calc_func = calc_func
        
    def get_value_for_datastore(self, model_instance):
        return self.calc_func(model_instance)

        
def calculated_property(calc_func):
    return CalculatedProperty(calc_func=calc_func)


def generate_keywords(string):
    return (word.lower() for word in string.split())

class Campaign(db.Model):
    description = db.TextProperty()
    system = db.StringProperty()
    gamemasters = db.ListProperty(users.User)
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    
    @calculated_property
    def keywords(model_instance):
        value = []
        value.extend(generate_keywords(model_instance.key().name()))
        value.extend(generate_keywords(model_instance.system))
        for user in model_instance.gamemasters:
            value.extend(generate_keywords(user.nickname()))
        return value

class ETag(object):
    version_hash = hashlib.sha1()
    version_hash.update('Version: %r\n' % (hex(version.HGVERSION),))

    def __init__(self):
        self._hash = self.version_hash.copy()
            
    def update(self, tag, s):
        self._hash.update('%s: %r\n' % (tag, s))
        
    def __str__(self):
        return self._hash.hexdigest()


class PageRequestHandler(webapp.RequestHandler):

    def __init__(self):
        self.user = users.get_current_user()

    def get(self):
        self.page = self.page_factory()
        if self.page.protected and not self.user:
            self.redirect(users.create_login_url(self.request.uri))
        user_id = self.user.user_id() if self.user else None
        etag = ETag()
        etag.update('User', user_id)
        for key, value in self.page.generate_key_values():
            etag.update(key, value)
        etag_str = str(etag)
        self.response.headers['ETag'] = '"%s"' % (etag_str,)
        if etag_str in self.request.if_none_match:
            self.error(304)
            return
        self.page.update_form_data(self.request)
        self.render()
        
    def post(self):
        self.page = self.page_factory()
        if not hasattr(self.page, 'action'):
            self.error(405)
            return
        self.page.update_form_data(self.request)
        redirection = self.page.action(self.request, self.user)
        if redirection:
            self.error(303)
            self.response.headers['Location'] = redirection
            return
        self.render()

    def render(self):
        url = (users.create_logout_url(self.request.uri) if self.user
            else users.create_login_url(self.request.uri))
        if self.user:
            self.page.nickname = self.user.nickname()
        self.page.url = url
        self.page.update_page_data(self.user)
        self.page.render(self.response)


class Page(object):

    protected = False

    @classmethod
    def requestHandler(cls):
        return type("PageRequestHandler", (PageRequestHandler,), 
            {'page_factory': cls})

    def generate_key_values(self):
        return ()
        
    def update_form_data(self, request):
        pass

    def update_page_data(self, user):
        pass

    def render(self, response):
        path = os.path.join(os.path.dirname(__file__), self.template_file)
        response.out.write(template.render(path, self.__dict__))


class MainPage(Page):
    template_file = 'index.html'

    def update_form_data(self, request):
        self.keywords = request.get('keywords')

    def update_page_data(self, user):
        q = Campaign.all()
        for word in self.keywords.split():
            q.filter('keywords =', word.lower())
        q.order('-modified')
        q.order('__key__')
        self.campaigns = q.fetch(20)

    def generate_key_values(self):
        yield 'Counter', counter.get_count()


class AddPage(Page):

    template_file = 'add.html'
    protected = True

    def update_form_data(self, request):
        self.name = request.get('name')
        self.system = request.get('system', 'Unspecified')
        self.description = request.get('description')

    def action(self, request, user):
        if not user:
            self.error_msg = (
                u"Not logged in. Please log in before you proceed.")
            return

        campaign = Campaign(key_name=self.name,
                            description=self.description,
                            system=self.system,
                            gamemasters=[user])
        # FIXME Bad key error if name is empty
        def txn():
            if Campaign.get_by_key_name(self.name):
                return False
            campaign.put()
            return True
        if db.run_in_transaction(txn):
            counter.increment()
            return request.relative_url('/') # FIXME
        self.error_msg = (
            u"There exists already a campaign by the name '%s'." % self.name)


application = webapp.WSGIApplication(
                                     [('/', MainPage.requestHandler()),
                                      ('/add.html', AddPage.requestHandler()),],
                                     debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()

