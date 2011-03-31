import urllib

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import BadKeyError

import counter
from error import ClientError


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
    new_applications = db.BooleanProperty(default=False)

    @property
    def name(self):
        return self.key().name()

    @calculated_property
    def keywords(model_instance):
        value = []
        value.extend(generate_keywords(model_instance.key().name()))
        value.extend(generate_keywords(model_instance.system))
        for user in model_instance.gamemasters:
            value.extend(generate_keywords(user.nickname()))
        return value

    @classmethod
    def get_by_quoted(cls, campaign):
        return cls.get_by_key_name(urllib.unquote_plus(campaign))

    def can_post(self, user):
        return True # FIXME TODO

    def is_gamemaster(self):
        try:
            return users.User() in self.gamemasters
        except users.UserNotFoundError:
            return False

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
        application = self.get_application()
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

    def players(self):
        q = Player.all()
        q.ancestor(self)
        q.order('user')
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


class Post(db.Model):
    version = db.DateTimeProperty(auto_now_add=True)


class Cast(db.Model):
    version = db.DateTimeProperty()
    characters = db.StringListProperty()


class Character(db.Model):

    @property
    def name(self):
        return self.key().name()


class CharacterVersion(db.Model):
    version = db.DateTimeProperty() # TODO: May into number and as part of key.

    @property
    def name(self):
        return self.parent.name        


def get_campaign(name):
    # TODO: Remove.
    return Campaign.get_by_key_name(name)

