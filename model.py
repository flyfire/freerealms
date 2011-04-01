import urllib

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import BadKeyError

import counter
from common import ComputedProperty, generate_keywords
from error import ClientError

class Campaign(db.Model):
    description = db.TextProperty()
    system = db.StringProperty()
    gamemasters = db.ListProperty(users.User)
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    new_applications = db.BooleanProperty(default=False)

    @ComputedProperty
    def keywords(model_instance):
        value = []
        value.extend(generate_keywords(model_instance.key().name()))
        value.extend(generate_keywords(model_instance.system))
        for user in model_instance.gamemasters:
            value.extend(generate_keywords(user.nickname()))
        return value

    @property
    def name(self):
        return self.key().name()

    def __str__(self):
        return self.name

    @classmethod
    def get_by_quoted(cls, campaign):
        return cls.get_by_key_name(urllib.unquote(campaign))

    def can_post(self):
        try:
            user = users.User()
        except users.UserNotFoundError:
            return False    
        if user in self.gamemasters:
            return True
        q = Player.all()
        q.anchestor(self)
        q.filter('__key__ =', user.user_id())
        return q.get()

    def is_gamemaster(self):
        try:
            return users.User() in self.gamemasters
        except users.UserNotFoundError:
            return False
            
    @property
    def url(self):
        return '/campaigns/%s/' % urllib.quote(self.name, '')

    @classmethod
    def find(cls, keywords):
        q = cls.all()
        for word in keywords.split():
            q.filter('keywords =', word.lower())
            q.order('-modified')
            q.order('__key__')
        return q.fetch(20)

    @classmethod
    def create(name, description, system):
        user = users.get_current_user()
        if not user:
            raise ClientError(
                u"Not logged in. Please log in before you proceed.")
        try:
            campaign = cls(
                key_name=name,
                description=description,
                system=system,
                gamemasters=[user])
        except BadKeyError:
            raise ClientError(
                u"'%s' is not a suitable campaign name." % name if name else
                u"Campaign name missing. Please fill in a campaign name.")
        def txn():
            if Campaign.get_by_key_name(name):
                raise ClientError(
                    u"There exists already a campaign by the name '%s'." %
                    name)
            campaign.put()
        db.run_in_transaction(txn)
        counter.increment('campaigns')
        return campaign

    def create_application(self, message):
        try:
            application = Application(
                parent=self,
                key_name=users.User().user_id(),
                message=message)
        except users.UserNotFoundError:
            raise ClientError(
                u"Not logged in. Please log in before you proceed.")
        application.put()
        self.new_applications = True
        self.put()
        return application

    def create_player(self, user):
        player = Player(parent=self, key_name=user.user_id(), user=user)
        player.put()
        return player
    
    def application(self, user_id=None):
        if not user_id:
            user_id = users.User().user_id()
        return Application.get_by_key_name(user_id, parent=self)

    def delete_application(self):
        application = self.application()
        if application:
            application.delete()
    
    def applications(self):
        self.new_applications = False
        self.put()
        q = Application.all()
        q.ancestor(self)
        q.order('-modified')
        q.order('user')
        return q.fetch(20)

    def player(self, user_id=None):
        if not user_id:
            user_id = users.User().user_id()
        return Player.get_by_key_name(user_id, parent=self)

    def players(self):
        q = Player.all()
        q.ancestor(self)
        q.order('user')
        return q.fetch(20)

    def create_character(self, name, short_desc, description):
        try:
            character = Character(
                parent=self,
                key_name=name,
                short_desc=short_desc,
                description=description)
        except BadKeyError:
            raise ClientError(
                u"'%s' is not a suitable character name." % name if name else
                u"Character name missing. Please fill in a character name.")
        character.put()
        return character

    def get_character(self, name):
        return Character.get_by_key_name(name, parent=self)

    def delete_character(self, name):
        character = self.get_character(name)
        if character:
            character.delete()

    def characters(self):
        q = Character.all()
        q.ancestor(self)
        q.order('__key__')
        return q.fetch(20)     
        
        
class Application(db.Model):
    modified = db.DateTimeProperty(auto_now=True)
    user = db.UserProperty(auto_current_user_add=True)
    message = db.TextProperty()

    @property
    def user_id(self):
        return self.key().name()

    @property
    def campaign(self):
        return self.parent()

    @classmethod
    def find(cls):
        try:
            q = cls.all()
            q.filter('user =', users.User())
            q.order('-modified')
            q.order('__key__')
            return q.fetch(20)
        except users.UserNotFoundError:
            return None


class Player(db.Model):
    user = db.UserProperty()
    characters = db.StringListProperty()
    
    @property
    def user_id(self):
        return self.key().name()
    
    @property
    def campaign(self):
        return self.parent()

    def __str__(self):
        return self.user.nickname()

    def non_characters(self):
        campaign_key = self.parent_key()
        q = Character.all()
        q.ancestor(campaign_key)
        q.order('__key__')
        result = q.fetch(20)
        return [character for character in result if character.name not in self.characters]

class Character(db.Model):

    short_desc = db.StringProperty(required=True)
    description = db.TextProperty()

    @property
    def campaign(self):
        return self.parent()
            
    @property
    def name(self):
        return self.key().name()
        
    def __str__(self):
        return self.name

    def players(self):
        q = Player.all()
        q.ancestor(self.parent_key())
        q.filter('characters =', self.name)
        q.order('user')
        return q.fetch(20)
        

class Post(db.Model):

    @property
    def version(self):
        return int(self.key.name)

