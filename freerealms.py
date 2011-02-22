import hashlib
import os

from google.appengine.dist import use_library
use_library('django', '1.2')
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import counter
import version

class CalculatedProperty(db.Property):
    data_type = None
    
    def __init__(self, verbose_name=None, calc_func=(lambda model_instance: None), **kwds):
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


class FreeRealmsRequestHandler(webapp.RequestHandler):
    protected = False

    def __init__(self):
        self.user = users.get_current_user()
        self.data = {}

    def get(self):
        if self.protected and not self.user:
            self.redirect(users.create_login_url(self.request.uri))
    
        user_id = self.user.user_id() if self.user else None
        etag = ETag()
        etag.update('User', user_id)
        for key, value in self.generate_key_values():
            etag.update(key, value)
        etag_str = str(etag)
        self.response.headers['ETag'] = '"%s"' % (etag_str,)
        if etag_str in self.request.if_none_match:
            self.error(304)
            return
            
        self.update_form_data()
        self.render()

    def render(self):
        url = (users.create_logout_url(self.request.uri) if self.user
            else users.create_login_url(self.request.uri))
        if self.user:
            self.data['nickname'] = self.user.nickname()
        self.data['url'] = url
        self.update_page_data()
        path = os.path.join(os.path.dirname(__file__), self.template_file)
        self.response.out.write(template.render(path, self.data))

    def post(self):
        if not hasattr(self, 'action'):
            self.error(405)
            return
        
        self.update_form_data()
        redirection = self.action()
        if redirection:
            self.error(303)
            self.response.headers['Location'] = redirection
            return
            
        self.render()    

    def generate_key_values(self):
        return ()

    def update_form_data(self):
        pass

    def update_page_data(self):
        pass


class MainHandler(FreeRealmsRequestHandler):
    template_file = 'index.html'

    def update_form_data(self):
        self.data['keywords'] = self.request.get('keywords')

    def update_page_data(self):
        q = Campaign.all()
        for word in self.data['keywords'].split():
            q.filter('keywords =', word.lower())
        q.order('-modified')
        q.order('__key__')
        self.data['campaigns'] = q.fetch(20)

    def generate_key_values(self):
        yield 'Counter', counter.get_count()


class AddHandler(FreeRealmsRequestHandler):
    template_file = 'add.html'
    protected = True

    def update_form_data(self):
        self.data['name'] = self.request.get('name')
        self.data['system'] = self.request.get('system', 'Unspecified')

    def action(self):
        if not self.user:
            self.data['error_msg'] = u"Not logged in. Please log in before you proceed."
            return
            
        name = self.data['name']
        campaign = Campaign(key_name=name,
                            system=self.data['system'],
                            gamemasters=[self.user])
        # FIXME Bad key error if name is empty
        def txn():
            if Campaign.get_by_key_name(name):
                return False
            campaign.put()
            return True
        if db.run_in_transaction(txn):
            counter.increment()
            return self.request.relative_url('/') # FIXME
        self.data['error_msg'] = u"There exists already a campaign by the name '%s'." % name


application = webapp.WSGIApplication(
                                     [('/', MainHandler),
                                      ('/add.html', AddHandler),],
                                     debug=True)


def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()

