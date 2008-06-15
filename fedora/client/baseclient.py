# -*- coding: utf-8 -*-
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Red Hat Author(s): Luke Macken <lmacken@redhat.com>
#                    Toshio Kuratomi <tkuratom@redhat.com>
#
'''Command line client for a user to interact with a Fedora Service.'''

import os
import stat
from os import path
import logging
import cPickle as pickle

from fedora import __version__
from fedora import _

log = logging.getLogger(__name__)

SESSION_FILE = path.join(path.expanduser('~'), '.fedora_session')

from fedora.client import AuthError
### FIXME: when porting to py3k syntax, no need for try: except
# pylint: disable-msg=W0403
try:
    from .proxyclient import ProxyClient
except SyntaxError:
    from proxyclient import ProxyClient
# pylint: enable-msg=W0403

class BaseClient(ProxyClient):
    '''
        A command-line client to interact with Fedora TurboGears Apps.
    '''
    def __init__(self, base_url, useragent=None, debug=False, username=None,
            password=None, session_cookie=None, cache_session=True):
        '''
        Arguments:
        :base_url: Base of every URL used to contact the server

        Keyword Arguments:
        :useragent: useragent string to use.  If not given, default to
            "Fedora BaseClient/VERSION"
        :debug: If True, log debug information
        :username: username for establishing authenticated connections
        :password: password to use with authenticated connections
        :session_cookie: user's session_cookie to connect to the server
        :cache_session: if set to true, cache the user's session cookie on the
            filesystem between runs.
        '''
        self.useragent = useragent or 'Fedora BaseClient/%(version)s' % {
                'version': __version__}
        super(BaseClient, self).__init__(base_url, useragent=useragent,
                debug=debug)
        self.username = username
        self.password = password
        self.cache_session = cache_session
        self._session_cookie = None
        if session_cookie:
            self.session_cookie = session_cookie

    def __load_cookies(self):
        '''load cookie data from a file.

        Returns: the complete mapping of users to session cookies.
        '''
        saved_session = {}
        if path.isfile(SESSION_FILE):
            session_file = file(SESSION_FILE, 'r')
            try:
                saved_session = pickle.load(session_file)
            except EOFError:
                log.info(_('Unable to load session from %(file)s') % \
                        {'file': SESSION_FILE})
            session_file.close()

        return saved_session

    def __save_cookies(self, save):
        '''Save the cached cookies file.

        Arguments:
        :save: The dict of usernames to cookies to save.
        '''
        try:
            session_file = file(SESSION_FILE, 'w')
            os.chmod(SESSION_FILE, stat.S_IRUSR | stat.S_IWUSR)
            pickle.dump(save, session_file)
            session_file.close()
        except Exception, e: # pylint: disable-msg=W0703
            # If we can't save the file, issue a warning but go on.  The
            # session just keeps you from having to type your password over
            # and over.
            log.warning(_('Unable to write to session file %(session)s:' \
                    ' %(error)s') % {'session': SESSION_FILE, 'error': str(e)})

    def _get_session_cookie(self):
        '''Attempt to retrieve the session cookie from the filesystem.'''
        # If none exists, return None
        if self._session_cookie:
            return self._session_cookie
        saved_sessions = self.__load_cookies()
        self._session_cookie = saved_sessions.get(self.username, '')
        if not self._session_cookie:
            log.debug(_('No session cached for "%s"') % self.username)

        return self._session_cookie

    def _set_session_cookie(self, session_cookie):
        '''Store our pickled session cookie.

        Arguments:
        :session_cookie: cookie to set our internal cookie to

        This method loads our existing session file and modifies our
        current user's cookie.  This allows us to retain cookies for
        multiple users.
        '''
        # Start with the previous users
        if self.cache_session and self.username:
            save = self.__load_cookies()
            save[self.username] = session_cookie
            # Save the cookies to the filesystem
            self.__save_cookies(save)
        self._session_cookie = session_cookie

    def _del_session_cookie(self):
        '''Delete the session cookie from the filesystem.'''
        # Start with the previous users
        save = self.__load_cookies()
        try:
            del save[self.username]
        except KeyError:
            # This is fine we just want the session to exist in the new
            # session file.
            pass
        else:
            # Save the cookies to the filesystem
            self.__save_cookies(save)
        self._session_cookie = None

    session_cookie = property(_get_session_cookie, _set_session_cookie, 
            _del_session_cookie, '''The session_cookie.

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
        del(self.session_cookie)

    def send_request(self, method, req_params=None, auth=True):
        '''Make an HTTP request to a server method.

        The given method is called with any parameters set in req_params.  If
        auth is True, then the request is made with an authenticated session
        cookie.

        Arguments:
        :method: Method to call on the server.  It's a url fragment that comes
            after the base_url set in __init__().
        :req_params: Extra parameters to send to the server.
        :auth: If True perform auth to the server, else do not.
        '''
        if auth == True:
            # We need something to do auth.  Check user/pass
            if not self.username and self.password:
                # No?  Check for session_cookie
                if not self.session_cookie:
                    raise AuthError, 'Auth was requested but no way to' \
                            ' perform auth was given.  Please set username' \
                            ' and password or session_cookie before calling' \
                            ' this function with auth=True'

        auth_params = {'username': self.username, 'password': self.password,
                'cookie': self.session_cookie}
        # Remove empty params
        # pylint: disable-msg=W0104
        [auth_params.__delitem__(key) for key, value in auth_params.items()
                if not value]
        # pylint: enable-msg=W0104

        session_cookie, data = super(BaseClient, self).send_request(method,
                req_params = req_params, auth_params = auth_params)
        # In case the server returned a new session cookie to us
        if self.session_cookie != session_cookie:
            self.session_cookie = session_cookie

        return data
