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

    # TODO: template_values into RequestHandler
    def render(self, template_file, template_values):
        path = template_path(template_file)
        self.response.out.write(template.render(path, template_values))

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
            'applications' : model.Application.find(),
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
            model.Campaign.create(form.name, form.description, form.system)
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
            'campaign' : campaign,
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
            'campaign' : campaign,
        }       
        path = template_path('description.html')
        self.response.out.write(template.render(path, template_values))


class NewPage(FreeRealmsRequestHandler):

    def get(self, campaign):
        campaign = Campaign.get_by_quoted(campaign)
        if not campaign:
            self.error(404)
            return
        user = users.get_current_user()
        if not user or not campaign.can_post(user):
            self.redirect(users.create_login_url(self.request.uri))
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign,
        }
        path = template_path('new.html')
        self.response.out.write(template.render(path, template_values))


class ApplicationPage(FreeRealmsRequestHandler):

    class FormData(object):
    
        def __init__(self, request):
            self.message = request.get('message')

    def form_data(self):
        return self.FormData(self.request)

    def get(self, campaign):
        campaign = model.Campaign.get_by_quoted(campaign)
        if not campaign:
            self.error(404)
            return
        if not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
        form = self.form_data()
        application = campaign.application()
        if application:
            form.message = application.message
        template_values = {
            'form' : form,
            'user' : self.user_info(),
            'campaign' : campaign,
        }
        path = template_path('application.html')
        self.response.out.write(template.render(path, template_values))

    def post(self, campaign):
        campaign = model.Campaign.get_by_quoted(campaign)
        if not campaign:
            self.error(404)
            return
        form = self.form_data()
        action = self.request.get('action', 'apply')
        try:
            if action == 'apply':
                campaign.create_application(form.message)
            else:
                campaign.delete_application()
            url = '/'
            self.redirect(self.request.relative_url(url, to_application=True))
        except ClientError as e:
            template_values = {
                'form' : form,
                'user' : self.user_info(),
                'campaign': campaign,
                'error_msg' : e.msg
            }
            path = template_path('application.html')
            self.response.out.write(template.render(path, template_values))

class ApplicationsPage(FreeRealmsRequestHandler):

    def get(self, campaign):
        campaign = model.Campaign.get_by_quoted(campaign)
        if not campaign:
            self.error(404)
            return
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        applications = campaign.applications()
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign,
            'applications' : applications
        }
        path = template_path('applications.html')
        self.response.out.write(template.render(path, template_values))

    def post(self, campaign):
        campaign = model.Campaign.get_by_quoted(campaign)
        if not campaign:
            self.error(404)
            return
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        accept = self.request.get('accept')
        reject = self.request.get('reject')
        user_id = accept or reject
        if user_id:
            application = campaign.application(user_id)
        if accept and application:
            campaign.create_player(application.user)                            
            application.delete()
        if reject and application:
            application.delete()
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign,
            'applications' : campaign.applications()
        }
        path = template_path('applications.html')
        self.response.out.write(template.render(path, template_values))


class PlayersPage(FreeRealmsRequestHandler):

    def get(self, campaign):
        campaign = model.Campaign.get_by_quoted(campaign)
        if not campaign:
            self.error(404)
            return
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        players = campaign.players()
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign,
            'players' : players,
        }
        self.render('players.html', template_values)

    def post(self, campaign):
        pass # TODO

class CharactersPage(FreeRealmsRequestHandler):

    def get(self, campaign):
        campaign = model.Campaign.get_by_quoted(campaign)
        template_values = {
            'user' : self.user_info(),
            'campaign' : campaign
        }
        self.render('characters.html', template_values)

class CharacterPage(FreeRealmsRequestHandler):

    def get(self, campaign, character):
        campaign = model.Campaign.get_by_quoted(campaign)
        

application = webapp.WSGIApplication(
    [
        ('/', MainPage),
        ('/add', AddPage),
        ('/campaigns/(.*)/', CampaignPage),
        ('/campaigns/(.*)/new', NewPage),
        ('/campaigns/(.*)/description', DescriptionPage),
        ('/campaigns/(.*)/application', ApplicationPage),
        ('/campaigns/(.*)/characters', CharactersPage),
        ('/campaigns/(.*)/applications', ApplicationsPage),
        ('/campaigns/(.*)/players', PlayersPage),
        ('/campaigns/(.*)/characters/(.*)/', CharacterPage),
    ], debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()

