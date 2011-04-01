import urllib

from google.appengine.dist import use_library
use_library('django', '1.2')

#os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
#from django.conf import settings
#settings._targets = None

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

from common import FreeRealmsRequestHandler, wsgi_application
import counter
from error import ClientError
import model
import campaign

template.register_template_library('common.templatefilters')


class MainPage(FreeRealmsRequestHandler):

    url = r'/'
    template = 'index.html'
            
    def get(self):
        campaign_count = counter.get_count('campaigns')
        keywords = request.get('keywords')
        self.render(
            campaign_count=campaign_count,
            applications=model.Application.find(),
            campaigns=model.Campaign.find(keywords))


class AddPage(FreeRealmsRequestHandler):

    url = r'/add'
    template = 'add.html'

    def get(self):
        if not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
        self.render()

    def post(self):
        name = request.get('name')
        system = request.get('system', 'Unspecified')
        description = request.get('description')        
        try:
            campaign = model.Campaign.create(name, description, system)
            self.relative_redirect(campaign.url)
        except ClientError, e:
            self.render(
                name=name, system=system, description=description,
                error_msg=e.msg)


application = wsgi_application(debug=True)


def main():
    run_wsgi_app(application)


if __name__ == '__main__':
    main()

