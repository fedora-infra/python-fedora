'''
This plugin provides integration with the Fedora Account System using JSON
calls to the account system server.
'''

import Cookie

from turbogears import config
from turbogears.visit.api import Visit, BaseVisitManager

from fedora.client import ProxyClient

from fedora import _, __version__

import logging
log = logging.getLogger("turbogears.identity.savisit")

class JsonFasVisitManager(BaseVisitManager):
    '''
    This proxies visit requests to the Account System Server running remotely.

    We don't need to worry about threading and other concerns because our proxy
    doesn't cause any asynchronous calls.
    '''
    fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/admin/fas')
    cookie_name = config.get('visit.cookie.name', 'tg-visit')
    fas = None

    def __init__(self, timeout, debug=None):
        self.debug = debug or False
        if not self.fas:
            self.fas = ProxyClient(self.fas_url, debug=self.debug,
                    useragent='JsonFasVisitManager/%s' % __version__)
        BaseVisitManager.__init__(self, timeout)

    def create_model(self):
        '''
        Create the Visit table if it doesn't already exist.

        Not needed as the visit tables reside remotely in the FAS2 database.
        '''
        pass

    def new_visit_with_key(self, visit_key):
        '''
        Return a new Visit object with the given key.
        '''
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        old_cookie = Cookie.SimpleCookie()
        old_cookie[self.cookie_name] = visit_key
        session_cookie, data = self.fas.send_request('',
                auth_params={'cookie': old_cookie})
        return Visit(session_cookie[self.cookie_name].value, True)

    def visit_for_key(self, visit_key):
        '''
        Return the visit for this key or None if the visit doesn't exist or has
        expired.
        '''
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        old_cookie = Cookie.SimpleCookie()
        old_cookie[self.cookie_name] = visit_key
        session_cookie, data = fas.send_request('',
                auth_params={'cookie': old_cookie})
        # Knowing what happens in turbogears/visit/api.py when this is called,
        # we can shortcircuit this step and avoid a round trip to the FAS
        # server.
        # if visit_key != self._session_cookie[self.cookie_name].value:
        #     # visit has expired
        #     return None
        # # Hitting FAS has already updated the visit.
        # return Visit(visit_key, False)
        if visit_key != session_cookie[self.cookie_name].value:
            return Visit(session_cookie[self.cookie_name].value, True)
        else:
            return Visit(visit_key, False)

    def update_queued_visits(self, queue):
        '''Update the visit information on the server'''
        # Hit any URL in fas with each visit_key to update the sessions
        for visit_key in queue:
            log.info(_('updating visit (%s)'), visit_key)
            old_cookie = Cookie.SimpleCookie()
            old_cookie[self.cookie_name] = visit_key
            fas.send_request('', auth=True)
