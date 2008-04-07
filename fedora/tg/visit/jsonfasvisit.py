'''
This plugin provides integration with the Fedora Account System using JSON
calls to the account system server.
'''

import Cookie

from turbogears import config
from turbogears.visit.api import Visit, BaseVisitManager

from fedora.tg.client import BaseClient

import gettext
t = gettext.translation('python-fedora', '/usr/share/locale', fallback=True)
_ = t.ugettext

import logging
log = logging.getLogger("turbogears.identity.savisit")

class JsonFasVisitManager(BaseVisitManager):
    '''
    This proxies visit requests to the Account System Server running remotely.

    We don't need to worry about threading and other concerns because our proxy
    doesn't cause any asynchronous calls.
    '''
    fasURL = config.get('fas.url', 'https://admin.fedoraproject.org/admin/fas')
    cookieName = config.get('visit.cookie.name', 'tg-visit')

    def __init__(self, timeout, debug=None):
        self.debug = debug or False
        BaseVisitManager.__init__(self, timeout, debug=debug)

    def create_model(self):
        '''
        Create the Visit table if it doesn't already exist.

        Not needed as the visit tables reside remotely in the FAS2 database.
        '''
        pass

    def new_visit_with_key(self, visit_key):
        '''
        Return a new Visit objectwith the given key.
        '''
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        fas = BaseClient(self.fasURL, self.debug)
        fas._sessionCookie = Cookie.SimpleCookie()
        fas._sessionCookie[self.cookieName] = visit_key
        data = fas.send_request('', auth=True)
        return Visit(fas._sessionCookie[self.cookieName].value, True)

    def visit_for_key(self, visit_key):
        '''
        Return the visit for this key or None if the visit doesn't exist or has
        expired.
        '''
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        fas = BaseClient(self.fasURL, self.debug)
        fas._sessionCookie = Cookie.SimpleCookie()
        fas._sessionCookie[self.cookieName] = visit_key
        data = fas.send_request('', auth=True)
        # Knowing what happens in turbogears/visit/api.py when this is called,
        # we can shortcircuit this step and avoid a round trip to the FAS
        # server.
        # if visit_key != self._sessionCookie[self.cookieName].value:
        #     # visit has expired
        #     return None
        # # Hitting FAS has already updated the visit.
        # return Visit(visit_key, False)
        if visit_key != fas._sessionCookie[self.cookieName].value:
            return Visit(fas._sessionCookie[self.cookieName].value, True)
        else:
            return Visit(visit_key, False)

    def update_queued_visits(self, queue):
        '''Update the visit information on the server'''
        fas = BaseClient(self.fasURL, self.debug)
        for visit_key in queue:
            log.info("updating visit (%s)", visit_key)
            fas._sessionCookie = Cookie.SimpleCookie()
            fas._sessionCookie[self.cookieName] = visit_key
            data = fas.send_request('', auth=True)
            fas.send_request()
