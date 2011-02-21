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


MSG_NOT_LOGGED_IN = u"Not logged in. Please log in before you proceed."

class Campaign(db.Model):
    description = db.TextProperty()
    game_system = db.StringProperty()
    game_masters = db.ListProperty(users.User)
    created = db.DateTimeProperty(auto_now_add=True)
    
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
        self.update_etag(etag)
        etag_str = str(etag)
        self.response.headers['ETag'] = '"%s"' % (etag_str,)
        if etag_str in self.request.if_none_match:
            self.error(304)
        else:
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

    def update_etag(self, etag):
        pass

    def update_form_data(self):
        pass

    def update_page_data(self):
        pass

class MainHandler(FreeRealmsRequestHandler):
    template_file = 'index.html'

    def update_etag(self, etag):
        etag.update('Counter', counter.get_count())

class AddHandler(FreeRealmsRequestHandler):
    template_file = 'add.html'
    protected = True

    def update_form_data(self):
        self.data['campaign'] = self.request.get('campaign')
        self.data['game_system'] = self.request.get('game_system', 'Unspecified')
        
    def post(self):
        self.update_form_data()

        if self.user:
            name = self.data['campaign']
            campaign = Campaign(key_name=name,
                                game_system=self.data['game_system'],
                                game_masters=[self.user])
            def txn():
                if Campaign.get_by_key_name(name):
                    return False
                campaign.put()
                return True
            if db.run_in_transaction(txn):
                counter.increment()
                self.error(303)
                self.response(users.create_login_url(self.request.relative_url('')))
                return
            else:
                data['error_msg'] = u"There exists already a campaign by the name '%s'." % data.campaign
        else:
            data['error_msg'] = MSG_NOT_LOGGED_IN

        self.render()

application = webapp.WSGIApplication(
                                     [('/', MainHandler),
                                      ('/add.html', AddHandler),],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

