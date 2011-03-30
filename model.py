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
    
    @calculated_property
    def keywords(model_instance):
        value = []
        value.extend(generate_keywords(model_instance.key().name()))
        value.extend(generate_keywords(model_instance.system))
        for user in model_instance.gamemasters:
            value.extend(generate_keywords(user.nickname()))
        return value


def get_campaign(name):
    return Campaign.get_by_key_name(name)


def find_campaigns(keywords):
    q = Campaign.all()
    for word in keywords.split():
        q.filter('keywords =', word.lower())
        q.order('-modified')
        q.order('__key__')
    return q.fetch(20)


def create_campaign(name, description, system):
    user = users.get_current_user()
    if not user:
        raise ClientError(u"Not logged in. Please log in before you proceed.")
    try:  
        campaign = Campaign(
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
                u"There exists already a campaign by the name '%s'." % name)
        campaign.put()
    db.run_in_transaction(txn)
    counter.increment('campaigns')

