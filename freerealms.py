import os
import urllib

from google.appengine.dist import use_library
use_library('django', '1.2')

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
#from django.conf import settings
#settings._targets = None

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import counter
from error import ClientError
import model


template.register_template_library('common.templatefilters')


def template_path(template):
    return os.path.join(os.path.dirname(__file__), 'templates', template)


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

    class FormData(object):
        def __init__(self, request):
            self.keywords = request.get('keywords')
            
    def form_data(self):
        return self.FormData(self.request)

    def get(self):
        form = self.form_data()
        campaign_count = counter.get_count('campaigns')
        template_values = {
            'user' : self.user_info(),
            'campaign_count': campaign_count,
            'form' : form,
            'campaigns' : model.Campaign.find(form.keywords)
        }
        path = template_path('index.html')
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
        path = template_path('add.html')
        self.response.out.write(template.render(path, template_values))
    
    def post(self):
        form = self.form_data()
        try:
            model.create_campaign(form.name, form.description, form.system)
            url = '/campaigns/%s' % urllib.quote(form.name, '')
            self.redirect(self.request.relative_url(url, to_application=True))
        except ClientError as e:
            template_values = {
                'form' : form,
                'user' : self.user_info(),
                'error_msg' : e.msg
            }
            path = template_path('add.html')
            self.response.out.write(template.render(path, template_values))


class CampaignPage(FreeRealmsRequestHandler):

    def get(self, campaign):
        campaign = model.get_campaign(urllib.unquote(campaign))
        if not campaign:
            self.error(404)
            return
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign
        }       
        path = template_path('campaign.html')
        self.response.out.write(template.render(path, template_values))


class DescriptionPage(FreeRealmsRequestHandler):

    def get(self, campaign):
        campaign = model.get_campaign(urllib.unquote(campaign))
        if not campaign:
            self.error(404)
            return
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign
        }       
        path = template_path('description.html')
        self.response.out.write(template.render(path, template_values))


class NewPage(FreeRealmsRequestHandler):

    def get(self, campaign):
        campaign = model.get_campaign(urllib.unquote(campaign))
        if not campaign:
            self.error(404)
            return
        user = users.get_current_user()
        if not user or not campaign.can_post(user):
            self.redirect(users.create_login_url(self.request.uri))
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign
        }
        path = template_path('new.html')
        self.response.out.write(template.render(path, template_values))


application = webapp.WSGIApplication(
    [
        ('/', MainPage),
        ('/add', AddPage),
        ('/campaigns/(.*)/', CampaignPage),
        ('/campaigns/(.*)/new', NewPage),
        ('/campaigns/(.*)/description', DescriptionPage),
    ], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()

