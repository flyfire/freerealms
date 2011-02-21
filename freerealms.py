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


class Campaign(db.Model):
    description = db.TextProperty()
    gameSystem = db.StringProperty()

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

    def __init__(self):
        self.template_values = {}

    def get(self):
        self.user = users.get_current_user()
        nickname = self.user.nickname() if self.user else None
        etag = ETag()
        etag.update('Nickname', nickname)
        self.update_etag(etag)
        etag_str = str(etag)
        self.response.headers['ETag'] = '"%s"' % (etag_str,)
        if etag_str in self.request.if_none_match:
            self.error(304)
            return
        
        url = (users.create_logout_url(self.request.uri) if nickname
            else users.create_login_url(self.request.uri))
        template_values = {
            'nickname' : nickname,
            'url'      : url
        }
        self.update_template(template_values)
        path = os.path.join(os.path.dirname(__file__), self.template_file)
        self.response.out.write(template.render(path, template_values))
        
    def update_etag(self, etag):
        pass
    
    def update_template(self, template_values):
        pass
    

class MainHandler(FreeRealmsRequestHandler):
    template_file = 'index.html'

    def update_etag(self, etag):
        etag.update('Counter', counter.get_count())


class AddHandler(FreeRealmsRequestHandler):
    template_file = 'add.html'

application = webapp.WSGIApplication(
                                     [('/', MainHandler),
                                      ('/add', AddHandler),],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

