import os

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from _common import root_path

QUOTED_GROUP = r'([a-zA-Z0-9_\.\-%]+)'


class ComputedProperty(db.Property):
    data_type = None
    
    def __init__(self, derive_func, *args, **kwargs):
        """Constructor.
        
        Args:
          derive_func: A function that takes on argument, the model isntance,
                       and returns a calculated value.
        """
        super(ComputedProperty, self).__init__(*args, **kwargs)
        self.__derive_func = derive_func    
        
    def get_value_for_datastore(self, model_instance):
        return self.__derive_func(model_instance)


def generate_keywords(string):
    return (word.lower() for word in string.split())


_url_mapping = []

def wsgi_application(debug=False):
    return webapp.WSGIApplication(_url_mapping, debug)


class MetaFreeRealmsRequestHandler(type):

    def __init__(cls, name, bases, dct):
        try:
            _url_mapping.append((cls.url, cls))
        except AttributeError:
            pass


class UserInfo(object):
    
    def __init__(self, request):
        user = users.get_current_user()
        if user:
            self.nickname = user.nickname()
            self.url = users.create_logout_url(request.uri)
        else:
            self.url = users.create_login_url(request.uri)


class FreeRealmsRequestHandler(webapp.RequestHandler):

    __metaclass__ = MetaFreeRealmsRequestHandler

    def render(self, **template_values):
        path = os.path.join(root_path, 'templates', self.template)
        template_values.setdefault('user', UserInfo(self.request))
        self.response.out.write(template.render(path, template_values))

    def relative_redirect(self, url):
        self.redirect(self.request.relative_url(url, to_application=True))

