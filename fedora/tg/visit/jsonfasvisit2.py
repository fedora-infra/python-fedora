# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008  Red Hat, Inc.
# This file is part of python-fedora
# 
# python-fedora is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# python-fedora is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with python-fedora; if not, see <http://www.gnu.org/licenses/>
#
# Adapted from code in the TurboGears project licensed under the MIT license.
#
'''
This plugin provides integration with the Fedora Account System using JSON
calls to the account system server.


.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''
import threading

from turbogears import config
from turbogears.visit.api import Visit, BaseVisitManager
from kitchen.text.converters import to_bytes

from fedora.client import FasProxyClient

from fedora import b_, __version__

import logging
log = logging.getLogger("turbogears.identity.jsonfasvisit")

class JsonFasVisitManager(BaseVisitManager):
    '''
    This proxies visit requests to the Account System Server running remotely.
    '''
    fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts')
    fas = None
    debug = config.get('jsonfas.debug', False)
    error_session_id = 0
    error_session_id_lock = threading.Lock()

    def __init__(self, timeout):
        self.log = log
        if not self.fas:
            JsonFasVisitManager.fas = FasProxyClient(self.fas_url,
                    debug=self.debug,
                    session_name=config.get('visit.cookie.name', 'tg-visit'),
                    useragent='JsonFasVisitManager/%s' % __version__,
                    retries=3)
        BaseVisitManager.__init__(self, timeout)
        self.log.debug('JsonFasVisitManager.__init__: exit')

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
        self.log.debug('JsonFasVisitManager.new_visit_with_key: enter')
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        # We only need to get the session cookie from this request
        try:
            request_data = self.fas.refresh_session(visit_key)
        except Exception:
            # HACK -- if we get an error from calling FAS, we still need to
            # return something to the application
            try:
                JsonFasVisitManager.error_session_id_lock.acquire()
                session_id = str(JsonFasVisitManager.error_session_id)
                JsonFasVisitManager.error_session_id += 1
            finally:
                JsonFasVisitManager.error_session_id_lock.release()
        else:
            session_id = request_data[0]
        self.log.debug('JsonFasVisitManager.new_visit_with_key: exit')
        return Visit(session_id, True)

    def visit_for_key(self, visit_key):
        '''
        Return the visit for this key or None if the visit doesn't exist or has
        expired.
        '''
        self.log.debug('JsonFasVisitManager.visit_for_key: enter')
        # Hit any URL in fas2 with the visit_key set.  That will call the
        # new_visit method in fas2
        # We only need to get the session cookie from this request
        try:
            request_data = self.fas.refresh_session(visit_key)
        except Exception:
            # HACK -- if we get an error from calling FAS, we still need to
            # return something to the application
            try:
                JsonFasVisitManager.error_session_id_lock.acquire()
                session_id = str(JsonFasVisitManager.error_session_id)
                JsonFasVisitManager.error_session_id += 1
            finally:
                JsonFasVisitManager.error_session_id_lock.release()
        else:
            session_id = request_data[0]

        # Knowing what happens in turbogears/visit/api.py when this is called,
        # we can shortcircuit this step and avoid a round trip to the FAS
        # server.
        # if visit_key != session_id:
        #     # visit has expired
        #     return None
        # # Hitting FAS has already updated the visit.
        # return Visit(visit_key, False)
        self.log.debug('JsonFasVisitManager.visit_for_key: exit')
        if visit_key != session_id:
            return Visit(session_id, True)
        else:
            return Visit(visit_key, False)

    def update_queued_visits(self, queue):
        '''Update the visit information on the server'''
        self.log.debug('JsonFasVisitManager.update_queued_visits: %s' % len(queue))
        # Hit any URL in fas with each visit_key to update the sessions
        for visit_key in queue:
            self.log.info(b_('updating visit (%s)'), to_bytes(visit_key))
            try:
                self.fas.refresh_session(visit_key)
            except Exception:
                # If fas returns an error, push the visit back onto the queue
                try:
                    self.lock.acquire()
                    self.queue[visit_key] = queue[visit_key]
                finally:
                    self.lock.release()
        self.log.debug('JsonFasVisitManager.update_queued_visitsr exit')
