import os

from google.appengine.dist import use_library
use_library('django', '1.2')

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from django.conf import settings
settings._targets = None

from google.appengine.api import users
from google.appengine.ext import db # TODO remove when no longer needed
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import rest

from model import Campaign

class UserInfo(object):
    
    def __init__(self, request):
        user = users.get_current_user()
        if user:
            self.nickname = user.nickname()
            self.url = users.create_logout_url(request.uri)
        else:
            self.url = users.create_login_url(request.uri)


class FreeRealmsRequestHandler(webapp.RequestHandler):

    def user_info(self):
        return UserInfo(self.request)


class MainPage(FreeRealmsRequestHandler):

    def get(self):
        template_values = {
            'user' : self.user_info()
        }
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class AddPage(FreeRealmsRequestHandler):

    class FormData(object):
    
        def __init__(self, request):
            self.name = request.get('name')
            self.system = request.get('system', 'Unspecified')
            self.description = request.get('description')

    def form_data(self):
        return self.FormData(self.request)

    def get(self):
        if not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
        template_values = {
            'user' : self.user_info()
        }
        path = os.path.join(os.path.dirname(__file__), 'add.html')
        self.response.out.write(template.render(path, template_values))
    
    def post(self):
        data = self.form_data()
                
        user = users.get_current_user()
        if not user:
            error_msg = u"Not logged in. Please log in before you proceed."
        else:
            campaign = Campaign(
                key_name=data.name,
                description=data.description,
                system=data.system,
                gamemasters=[user])
            # FIXME Bad key error if name is empty
            def txn():
                # TODO factor out
                if Campaign.get_by_key_name(data.name):
                    return False
                campaign.put()
                return True
            if db.run_in_transaction(txn):
                # counter.increment() # XXX
                # FIXME: Redirect to campaign page
                self.redirect(self.request.relative_url('/', to_application=True))
                return
            error_msg = u"There exists already a campaign by the name '%s'." % data.name
        
        template_values = {
            'data' : data,
            'user' : self.user_info(),
            'error' : error_msg
        }
        path = os.path.join(os.path.dirname(__file__), 'add.html')
        self.response.out.write(template.render(path, template_values))

application = webapp.WSGIApplication([('/', MainPage),
                                      ('/add', AddPage),
                                     ],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == '__main__':
    main()

