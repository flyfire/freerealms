import hashlib
import os

from google.appengine.dist import use_library
use_library('django', '1.2')

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings
settings._targets = None

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
        self.page = self.page_factory()
        self.page.user = users.get_current_user()

    def get(self):
        if self.page.protected and not self.page.user:
            self.redirect(users.create_login_url(self.request.uri))
        etag = ETag()
        for key, value in self.page.generate_key_values():
            etag.update(key, value)
        etag_str = str(etag)
        self.response.headers['ETag'] = '"%s"' % (etag_str,)
        if etag_str in self.request.if_none_match:
            self.error(304)
            return
        self.page.update_form_data(self.request)
        self.page.update_page_data(self.request)
        self.page.render(self.response)
        
    def post(self):
        for action in self.page.actions:
            if action in self.request.arguments():
                break
        else:
            self.error(405)
            return
        self.page.update_form_data(self.request)
        redirection = self.page.handler(action, self.request)
        if redirection:
            self.error(303)
            self.response.headers['Location'] = redirection
            return
        self.page.update_page_data(self.request)
        self.page.render(self.response)


class Page(object):
    params = ()
    protected = False

    @classmethod
    def requestHandler(cls):
        return type("PageRequestHandler", (PageRequestHandler,), 
            {'page_factory': cls})

    def generate_key_values(self):
        return ()
        
    def update_form_data(self, request):
        pass

    def update_page_data(self, request):
        pass

    def render(self, response):
        path = os.path.join(os.path.dirname(__file__), self.template_file)
        response.out.write(template.render(path, self.__dict__))


class FreeRealmsPage(Page):

    def update_page_data(self, request):
        self.user_url = (users.create_logout_url(request.uri)
            if self.user else users.create_login_url(request.uri))
        
    def generate_key_values(self):
        user_id = self.user.user_id() if self.user else None
        yield 'User', user_id


class MainPage(FreeRealmsPage):
    params = ('keyword,', 'describe')
    template_file = 'index.html'

    def update_form_data(self, request):
        self.describe = request.get('describe')
        self.keywords = request.get('keywords')

    def update_page_data(self, request):
        super(MainPage, self).__init__()
        q = Campaign.all()
        for word in self.keywords.split():
            q.filter('keywords =', word.lower())
        q.order('-modified')
        q.order('__key__')
        self.campaigns = q.fetch(20)
#        for campaign in self.campaigns:
#            self.campaign.show_url = 
#            self.campaign.hide_url = ''

    def generate_key_values(self):
        for key_value in super(MainPage, self).generate_key_values():
            yield key_value
        yield 'Counter', counter.get_count()


class AddPage(FreeRealmsPage):

    template_file = 'add.html'
    protected = True
    actions = ('add',)

    def update_form_data(self, request):
        self.name = request.get('name')
        self.system = request.get('system', 'Unspecified')
        self.description = request.get('description')

    def handler(self, action, request):
        if not self.user:
            self.error_msg = (
                u"Not logged in. Please log in before you proceed.")
            return

        campaign = Campaign(key_name=self.name,
                            description=self.description,
                            system=self.system,
                            gamemasters=[self.user])
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

