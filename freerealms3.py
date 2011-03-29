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

import counter # TODO implement several counters
import rest

import webpage
from webpage import action, application, PageProperty

from model import Campaign


class FreeRealmsPage(webpage.Page):

    def __call__(self, request):
        state = super(FreeRealmsPage, self).__call__(request)
        state.user = users.get_current_user()
        return state

    def update(self, instance, request):
        instance.user_url = (users.create_logout_url(request.uri)
            if instance.user else users.create_login_url(request.uri))
        instance.here = request.relative_url(self.url(instance), to_application=True)
        
    def generate_key_values(self, instance):
        user_id = instance.user.user_id() if instance.user else None
        yield 'User', user_id

    def render(self, instance, response):
        path = os.path.join(os.path.dirname(__file__), self.template_file)
        response.out.write(template.render(path, instance.__dict__))


@application.page
class MainPage(FreeRealmsPage):

    template_file = 'index.html'
    url_pattern = '/'

    class Model(FreeRealmsPage.Model):
        keywords = PageProperty(unicode, '')
        describe = PageProperty(unicode, '')

    def update_form_data(self, instance, request):
        instance.form_describe = request.get('form_describe')
        instance.form_keywords = request.get('form_keywords')

    @action("search")
    def search(self, instance, request):
        instance.keywords = instance.form_keywords
        return MainPage().absolute_url(instance, request)

    def update(self, instance, request):
        instance.add_url = AddPage().absolute_url(instance, request)

        super(MainPage, self).update(instance, request)
        q = Campaign.all()
        for word in instance.keywords.split():
            q.filter('keywords =', word.lower())
        q.order('-modified')
        q.order('__key__')
        instance.campaigns = q.fetch(20)
#        for campaign in self.campaigns:
#            self.campaign.show_url = self.absolute_url(instance, ... ?)
#            self.campaign.hide_url = ''

    def generate_key_values(self, instance):
        for key_value in super(MainPage, self).generate_key_values(instance):
            yield key_value
        yield 'Counter', counter.get_count()


@application.page
class AddPage(FreeRealmsPage):

    template_file = 'add.html'
    url_pattern = '/add'
   
    class Model(FreeRealmsPage.Model):
        keywords = PageProperty(unicode, '')
        describe = PageProperty(unicode, '')

    def isProtected(self):
        return True

    def update_form_data(self, instance, request):
        instance.name = request.get('name')
        instance.system = request.get('system', 'Unspecified')
        instance.description = request.get('description')

    @action('add')
    def add(self, instance, request):
        if not instance.user:
            instance.error_msg = (
                u"Not logged in. Please log in before you proceed.")
            return
        campaign = Campaign(key_name=instance.name,
                            description=instance.description,
                            system=instance.system,
                            gamemasters=[instance.user])
        # FIXME Bad key error if name is empty
        def txn():
            # TODO factor out
            if Campaign.get_by_key_name(instance.name):
                return False
            campaign.put()
            return True
        if db.run_in_transaction(txn):
            counter.increment()
            return MainPage().absolute_url(instance, request)    # FIXME
        instance.error_msg = (
            u"There exists already a campaign by the name '%s'." % instance.name)


wsgi_app = application.wsgi_app(debug=True)

def main():
    run_wsgi_app(wsgi_app)


if __name__ == "__main__":
    main()

