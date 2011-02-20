import hashlib
import os

from google.appengine.dist import use_library
use_library('django', '1.2')
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import version
version_hash = hashlib.sha1()
version_hash.update(hex(version.HGVERSION))        

class FreeRealmsRequestHandler(webapp.RequestHandler):

    def __init__(self):
        self._hash = version_hash.copy()
        self.template_values = {}
        self.user = users.get_current_user()
        if self.user:
            self._hash.update(self.user_id())
            self.template_values['nickname'] = self.user.nickname()
            self.template_values['url'] = users.create_logout_url(self.request.uri)
        else:
            self.template_values['url'] = users.create_login_url(self.request.uri)

    def update_hash(self, s):
        self._hash.update(s)

    def write_etag(self):
        etag = self._hash.hexdigest()
        self.response.headers['ETag'] = '%s"' % (etag,)
        if etag in self.request.if_none_match:
            self.response.set_status(304)
            return True
        return False

    def render(self, template_file):
        path = os.path.join(os.path.dirname(__file__), template_file)
        self.response.out.write(template.render(path, self.template_values))

class MainHandler(FreeRealmsRequestHandler):

    # TODO etag context manager
    def get(self):
        if self.write_etag():
            return
        self.render('index.html')


application = webapp.WSGIApplication(
                                     [('/', MainHandler)],
                                     debug=True)


def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

