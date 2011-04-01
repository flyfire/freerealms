from functools import wraps
from inspect import isfunction

from google.appengine.api import users

from common import FreeRealmsRequestHandler, QUOTED_GROUP
import model


def campaign_handler(*args, **kwargs):
    def decorator(func):
        @wraps(func)
        def wrapper(self, campaign, *args):
            campaign = model.Campaign.get_by_quoted(campaign)
            if not campaign:
                self.error(404)
                return
            if kwargs.get('gm_only') and not campaign.is_gamemaster():
                self.redirect(users.create_login_url(self.request.uri))
                return
            return func(self, campaign, *args)
        return wrapper
    if args:
        return decorator(args[0])
    else:
        return decorator


class CampaignPage(FreeRealmsRequestHandler):

    url = r'/campaign/%s/' % QUOTED_GROUP
    template = 'campaign.html'
    
    @campaign_handler
    def get(self, campaign):
        self.render(campaign=campaign)


class DescriptionPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/description' % QUOTED_GROUP
    template = 'description.html'

    @campaign_handler
    def get(self, campaign):
        self.render(campaign=campaign)

class NewPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/new' % QUOTED_GROUP
    template = '???'

    @campaign_handler
    def get(self, campaign):
        user = users.get_current_user()
        if not user or not campaign.can_post(user):
            self.redirect(users.create_login_url(self.request.uri))
        self.render(campaign=campaign)

class ApplicationPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/application' % QUOTED_GROUP
    template = 'application.html'

    @campaign_handler
    def get(self, campaign):
        if not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
        form = self.form_data()
        application = campaign.application()
        message = self.request.get('message',
            application.message if application else '')
        self.render(campaign=campaign, message=message)

    @campaign_handler
    def post(self, campaign):
        action = self.request.get('action', 'apply')
        message = self.request.get('message')
        try:
            if action == 'apply':
                campaign.create_application(message)
            else:
                campaign.delete_application()
            self.relative_redirect('/')
        except ClientError as e:
            self.render(campaign=campaign, message=message, error_msg=e.msg)


class ApplicationsPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/applications' % QUOTED_GROUP
    template = 'applications.html'
    
    @campaign_handler(gm_only=True)
    def get(self, campaign):
        self.render(campaign=campaign, applications=campaign.applications())

    @campaign_handler
    def post(self, campaign):
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
        self.render(campaign=campaign, applications=applications)


class PlayersPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/players' % QUOTED_GROUP
    template = 'players.html'

    @campaign_handler
    def get(self, campaign):
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        players = campaign.players()
        self.render(campaign=campaign, players=players)

    @campaign_handler
    def post(self, campaign):
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        handover = self.request.get('handover')
        user_id = handover
        if user_id:
            player = campaign.player(user_id)
        if player and handover:
            character = self.request.get('character')
            if not character in player.characters:
                player.characters.append(character)
            player.put()
        self.render(campaign=campaign, players=players) 


class CharactersPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/characters/' % QUOTED_GROUP
    template = 'characters.html'
    
    @campaign_handler
    def get(self, campaign):
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        self.render(campaign=campaign, characters=campaign.characters())

    @campaign_handler
    def post(self, campaign):
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        character = self.request.get('remove')
        if character:
            campaign.delete_character(character)
        self.render(campaign=campaign, characters=campaign.characters())
    

class AddCharacterPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/characters/add' % QUOTED_GROUP
    template = 'add_character.html'

    @campaign_handler    
    def get(self, campaign):
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        self.render(campaign=campaign)

    @campaign_handler
    def post(self, campaign):
        if not campaign.is_gamemaster():
            self.redirect(users.create_login_url(self.request.uri))
            return
        name = self.request.get('name')
        short_desc = self.request.get('short_desc')
        description = self.request.get('description')
        try:
            campaign.create_character(name, short_desc, description)
            self.relative_redirect(campaign.url + 'characters/')
        except ClientError as e:
            self.render(
                campaign=campaign, name=name, short_desc=short_desc,
                description=description, error_msg=e.msg)


class CharacterPage(FreeRealmsRequestHandler):

    url = r'/campaigns/%s/characters/%s/' % (QUOTED_GROUP, QUOTED_GROUP)
    template = 'character.html'
    
    def get(self, campaign, character):
        campaign = model.Campaign.get_by_quoted(campaign)

