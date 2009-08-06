# -*- coding: utf-8 -*-
#
# Copyright (C) 2007  Red Hat, Inc.
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
'''A base client for interacting with web services.

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

import os
import stat
from os import path
import logging
import cPickle as pickle
import Cookie
import warnings

from fedora import __version__
from fedora import _

log = logging.getLogger(__name__)

SESSION_DIR = path.join(path.expanduser('~'), '.fedora')
SESSION_FILE = path.join(SESSION_DIR, '.fedora_session')

from fedora.client import AuthError, ProxyClient

class BaseClient(ProxyClient):
    '''
        A client for interacting with web services.
    '''
    def __init__(self, base_url, useragent=None, debug=False, insecure=False,
            username=None, password=None, session_cookie=None,
            session_id=None, session_name='tg-visit', cache_session=True):
        '''
        :arg base_url: Base of every URL used to contact the server

        :kwarg useragent: Useragent string to use.  If not given, default to
            "Fedora BaseClient/VERSION"
        :kwarg session_name: name of the cookie to use with session handling
        :kwarg debug: If True, log debug information
        :kwarg insecure: If True, do not check server certificates against
            their CA's.  This means that man-in-the-middle attacks are
            possible against the `BaseClient`. You might turn this option on
            for testing against a local version of a server with a self-signed
            certificate but it should be off in production.
        :kwarg username: Username for establishing authenticated connections
        :kwarg password: Password to use with authenticated connections
        :kwarg session_cookie: *Deprecated* Use session_id instead.  If both
            session_id and session_cookie is given, only session_id will be
            used.  User's session_cookie to connect to the server.
        :kwarg session_id: id of the user's session
        :kwarg cache_session: If set to true, cache the user's session data on
            the filesystem between runs
        '''
        self.log = log
        self.useragent = useragent or 'Fedora BaseClient/%(version)s' % {
                'version': __version__}
        super(BaseClient, self).__init__(base_url, useragent=self.useragent,
                session_name=session_name, session_as_cookie=False,
                debug=debug, insecure=insecure)

        self.username = username
        self.password = password
        self.cache_session = cache_session
        self._session_id = None
        if session_id:
            self.session_id = session_id
        elif session_cookie:
            warnings.warn(_("session_cookie is deprecated, use session_id"
                    " instead"), DeprecationWarning, stacklevel=2)
            session_id = session_cookie.get(self.session_name, '')
            if session_id:
                self.session_id = session_id.value

    def __load_ids(self):
        '''load id data from a file.

        :Returns: Complete mapping of users to session ids
        '''
        saved_session = {}
        session_file = None
        if path.isfile(SESSION_FILE):
            try:
                session_file = file(SESSION_FILE, 'r')
                saved_session = pickle.load(session_file)
            except (IOError, EOFError):
                self.log.info(_('Unable to load session from %(file)s') % \
                        {'file': SESSION_FILE})
            if session_file:
                session_file.close()

        return saved_session

    def __save_ids(self, save):
        '''Save the cached ids file.

        :arg save: The dict of usernames to ids to save.
        '''
        # Make sure the directory exists
        if not path.isdir(SESSION_DIR):
            try:
                os.mkdir(SESSION_DIR, 0755)
            except OSError, e:
                self.log.warning(_('Unable to create %(dir)s: %(error)s') %
                    {'dir': SESSION_DIR, 'error': str(e)})

        try:
            session_file = file(SESSION_FILE, 'w')
            os.chmod(SESSION_FILE, stat.S_IRUSR | stat.S_IWUSR)
            pickle.dump(save, session_file)
            session_file.close()
        except Exception, e: # pylint: disable-msg=W0703
            # If we can't save the file, issue a warning but go on.  The
            # session just keeps you from having to type your password over
            # and over.
            self.log.warning(_('Unable to write to session file %(session)s:' \
                    ' %(error)s') % {'session': SESSION_FILE, 'error': str(e)})

    def _get_session_id(self):
        '''Attempt to retrieve the session id from the filesystem.

        Note: this method will cache the session_id in memory rather than fetch
        the id from the filesystem each time.

        :Returns: session_id
        '''
        if self._session_id:
            return self._session_id
        if not self.username:
            self._session_id = ''
        else:
            saved_sessions = self.__load_ids()
            self._session_id = saved_sessions.get(self.username, '')
        if isinstance(self._session_id, Cookie.SimpleCookie):
            self._session_id = ''

        if not self._session_id:
            self.log.debug(_('No session cached for "%s"') % self.username)

        return self._session_id

    def _set_session_id(self, session_id):
        '''Store our pickled session id.

        :arg session_id: id to set our internal id to

        This method loads our existing session file and modifies our
        current user's id.  This allows us to retain ids for
        multiple users.
        '''
        # Start with the previous users
        if self.cache_session and self.username:
            save = self.__load_ids()
            save[self.username] = session_id
            # Save the ids to the filesystem
            self.__save_ids(save)
        self._session_id = session_id

    def _del_session_id(self):
        '''Delete the session id from the filesystem.'''
        # Start with the previous users
        save = self.__load_ids()
        try:
            del save[self.username]
        except KeyError:
            # This is fine we just want the session to exist in the new
            # session file.
            pass
        else:
            # Save the ids to the filesystem
            self.__save_ids(save)
        self._session_id = None

    session_id = property(_get_session_id, _set_session_id,
            _del_session_id, '''The session_id.

        The session id is saved in a file in case it is needed in consecutive
        runs of BaseClient.
        ''')

    def _get_session_cookie(self):
        '''**Deprecated** Use session_id instead.

        Attempt to retrieve the session cookie from the filesystem.

        :Returns: user's session cookie
        '''
        warnings.warn(_('session_cookie is deprecated, use session_id'
            ' instead'), DeprecationWarning, stacklevel=2)
        session_id = self.session_id
        if not session_id:
            return ''
        cookie = Cookie.SimpleCookie()
        cookie[self.session_name] = session_id
        return cookie

    def _set_session_cookie(self, session_cookie):
        '''**Deprecated** Use session_id instead.
        Store our pickled session cookie.

        :arg session_cookie: cookie to set our internal cookie to

        This method loads our existing session file and modifies our
        current user's cookie.  This allows us to retain cookies for
        multiple users.
        '''
        warnings.warn(_('session_cookie is deprecated, use session_id'
            ' instead'), DeprecationWarning, stacklevel=2)
        session_id = session_cookie.get(self.session_name, '')
        if session_id:
            session_id = session_id.value
        self.session_id = session_id

    def _del_session_cookie(self):
        '''**Deprecated** Use session_id instead.

        Delete the session cookie from the filesystem.
        '''
        warnings.warn(_('session_cookie is deprecated, use session_id'
            ' instead'), DeprecationWarning, stacklevel=2)
        del(self.session_id)

    session_cookie = property(_get_session_cookie, _set_session_cookie, 
            _del_session_cookie, '''*Deprecated*, use session_id instead.

        The session cookie is saved in a file in case it is needed in
        consecutive runs of BaseClient.
        ''')

    def logout(self):
        '''Logout from the server.
        '''
        try:
            self.send_request('logout', auth=True)
        except AuthError: # pylint: disable-msg=W0704
            # We don't need to fail for an auth error as we're getting rid of
            # our authentication tokens here.
            pass
        del(self.session_id)

    def send_request(self, method, req_params=None, auth=False, **kwargs):
        '''Make an HTTP request to a server method.

        The given method is called with any parameters set in req_params.  If
        auth is True, then the request is made with an authenticated session
        cookie.

        :arg method: Method to call on the server.  It's a url fragment that
            comes after the base_url set in __init__().
        :kwarg req_params: Extra parameters to send to the server.
        :kwarg auth: If True perform auth to the server, else do not.
        :returns: The data from the server
        :rtype: DictContainer
        '''
        # Check for deprecated arguments.  This section can go once we hit 0.4
        if len(kwargs) >= 1:
            for arg in kwargs:
                # If we have extra args, raise an error
                if arg != 'input':
                    raise TypeError(_('send_request() got an unexpected' \
                            ' keyword argument "%s"') % arg)
            if req_params:
                # We don't want to allow input if req_params was already given
                raise TypeError(_('send_request() got an unexpected keyword' \
                        ' argument "input"'))
            if len(kwargs) > 1:
                # We shouldn't get here
                raise TypeError(_('send_request() got an unexpected keyword' \
                        ' argument'))

            # Error checking over, set req_params to the value in input
            warnings.warn(_('send_request(input) is deprecated.  Use' \
                    ' send_request(req_params) instead'), DeprecationWarning,
                    stacklevel=2)
            req_params = kwargs['input']

        auth_params = {'session_id': self.session_id}
        if auth == True:
            # We need something to do auth.  Check user/pass
            if self.username and self.password:
                # Add the username and password and we're all set
                auth_params['username'] = self.username
                auth_params['password'] = self.password
            else:
                # No?  Check for session_id
                if not self.session_id:
                    # Not enough information to auth
                    raise AuthError(_('Auth was requested but no way to' \
                            ' perform auth was given.  Please set username' \
                            ' and password or session_id before calling' \
                            ' this function with auth=True'))

        # Remove empty params
        # pylint: disable-msg=W0104
        [auth_params.__delitem__(key) for key, value in auth_params.items()
                if not value]
        # pylint: enable-msg=W0104

        session_id, data = super(BaseClient, self).send_request(method,
                req_params = req_params, auth_params = auth_params)
        # In case the server returned a new session id to us
        if self.session_id != session_id:
            self.session_id = session_id

        return data
