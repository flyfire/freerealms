from google.appengine.api import users
from google.appengine.ext import db

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

