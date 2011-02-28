from itertools import chain
import hashlib

from google.appengine.api import users
from google.appengine.ext import webapp

import version
version_hash = hashlib.sha1()
version_hash.update('%40x' % version.HGVERSION)


class StateVar(object):

    def __init__(self, factory, default):
        self._factory = factory
        self.default = default

    def decode(self, *strings):
        try:
            return self._factory(*strings)
        except AttributeError, TypeError:
            return self.default

    def encode(self, value):
        if value == self.default:
            return u''
        else:
            return unicode(value).encode('utf-8')


class State(dict):

    def __init__(self, request):
        super(State, self).__init__(self)
        self._request = request

    def update(self, *item):
        key, var = item
        self[key] = var.decode(*self._request.get_all(key))

    def update_for(self, page):
        for key, var in page.statevars().items():
            self.update(self, key, var)

    def url(self, page, **kwargs):
        query = []
        for key, var in sorted(page.statevars().items()):
            try:
                value = kwargs.get(key, self[key])
                encoded = var.encode(value)
                query.append((key, encoded))
            except KeyError:
                pass
        query_string = urllib.urlencode(query, doseq=True)
        url = '%s&%s' % (page.url_path(), query_string)
        return self.request.relative_url(url, to_application=True)


class Fragment(object):

    def initialize(self, state):
        pass

    def protected(self):
        return False

    def get_action(self, action):
        return None

    def render(self):
        return u''

    def tag(self):
        return None

    def update(self):
        pass


class Compound(Fragment):

    def init(self):
        self.fragments = {}

    def initialize(self, state):
        super(Compound, self).initialize(state)
        for fragment in self.fragments.values():
            fragment.initialize(state)

    def statevars(self):
        statevars = {}
        for fragment in self.fragments.values():
            statevars.update(fragment.statevars())

    def get_action(self, action):
        for fragment in self.fragments.values():
            action = fragment.get_action(self, action)
            if action:
                return action
        return None

    def protected(self):
        for fragment in self.fragments.values():
            if fragment.protected():
                return True
        return False

    def tag(self):
        return ((key, fragment.tag()) for key, fragment
                in self.fragments.items())

    def update(self):
        for fragment in self.fragments.values():
            fragment.update()


class Page(Compound):

    @classmethod
    def requestHandler(cls):
        requestHandler = RequestHandler
        requestHandler.page_factory = cls
        return requestHandler
            
    def url_path(self):
        return self.url_pattern


class RequestHandler(webapp.RequestHandler):

    def __init__(self):
        self.state = State(self.request)

    def get(self, *args):
        page = self.page_factory(*args)
        self.state.update_for(page)
        page.initialize(state)
        if page.isProtected() and not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
        h = version_hash.copy()
        h.update(repr(page.tag()))
        etag = h.hexdigest()
        self.response.headers['ETag'] = '"%s"' % etag
        if etag in self.request.if_none_match:
            self.error(304)
            return
        page.update()
        self.response.out.write(page.render())

    def post(self, *args):
        page = self.page_factory(*args)
        self.state.update_for(page)
        value = self.request.get('action', '')
        action = page.get_action(value) if value else None
        if not action:
            self.error(405)
            return
        redirection = action()
        if redirection:
            self.error(303)
            self.response.headers['Location'] = redirection
        page.update()
        self.response.out.write(page.render())


class Application(object):

    def __init__(self):
        self.url_mapping = []

    def page(self, cls):
        self.url_mapping.append((cls.url_pattern, cls.requestHandler()))
        return cls

    def wsgi_app(self, debug=False):
        return webapp.WSGIApplication(self.url_mapping, debug)


application = Application()
