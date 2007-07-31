# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
#
# Authors: Luke Macken <lmacken@redhat.com>
#          Toshio Kuratomi <tkuratom@redhat.com>
# Copyright: 2007 Red Hat Inc

import Cookie
import urllib
import urllib2
import logging
import cPickle as pickle
import re
from os import path

try:
    import simplejson
except ImportError:
    import json

log = logging.getLogger(__name__)

SESSION_FILE = path.join(path.expanduser('~'), '.fedora_session')

class ServerError(Exception):
    pass

class AuthError(ServerError):
    pass

class BaseClient(object):
    '''
        A command-line client to interact with Fedora TurboGears Apps.
    '''
    def __init__(self, baseURL, username=None, password=None):
        self.baseURL = baseURL
        self.username = username
        self.password = password
        self._sessionCookie = None
        self._load_session()
        if username and password:
            self._authenticate()

    def _authenticate(self):
        '''
            Return an authenticated session cookie.
        '''
        if self._sessionCookie:
            return self._sessionCookie

        if not self.username:
            raise AuthError, 'username must be set'
        if not self.password:
            raise AuthError, 'password must be set'

        req = urllib2.Request(self.baseURL + 'login?tg_format=json')
        req.add_data(urllib.urlencode({
                'user_name' : self.username,
                'password'  : self.password,
                'login'     : 'Login'
        }))

        try:
            loginPage = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            if e.msg == 'Forbidden':
                raise AuthError, 'Invalid username/password'

        try:
            loginData = simplejson.load(loginPage)
        except NameError:
            loginData = json.read(loginPage.read())

        if 'message' in loginData:
            raise AuthError, 'Unable to login to server: %s' % loginData['message']

        self._sessionCookie = Cookie.SimpleCookie()
        try:
            self._sessionCookie.load(loginPage.headers['set-cookie'])
        except KeyError:
            self._sessionCookie = None
            raise AuthError, 'Unable to login to the server.  Server did not' \
                             'send back a cookie.'
        self._save_session()

        return self._sessionCookie
    session = property(_authenticate)

    def _save_session(self):
        '''
            Store a pickled session cookie.
        '''
        sessionFile = file(SESSION_FILE, 'w')
        pickle.dump(self._sessionCookie, sessionFile)
        sessionFile.close()

    def _load_session(self):
        '''
            Load a stored session cookie.
        '''
        if path.isfile(SESSION_FILE):
            sessionFile = file(SESSION_FILE, 'r')
            try:
                self._sessionCookie = pickle.load(sessionFile)

                log.debug('Loaded session %s' % self._sessionCookie)
            except EOFError:
                log.error('Unable to load session from %s' % SESSION_FILE)
            sessionFile.close()

    def send_request(self, method, auth=False, input=None):
        '''
            Send a request to the server.  The given method is called with any
            keyword parameters in **kw.  If auth is True, then the request is
            made with an authenticated session cookie.
        '''
        url = self.baseURL + method + '/?tg_format=json'

        response = None # the JSON that we get back from the server
        data = None     # decoded JSON via json.read()

        log.debug('Creating request %s' % url)
        req = urllib2.Request(url)
        if input:
            req.add_data(urllib.urlencode(input))

        if auth:
            req.add_header('Cookie', self.session.output(attrs=[],
                                                   header='').strip())
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            log.error(e)
            raise ServerError, str(e)

        try:
            data = simplejson.load(response)
        except NameError:
            try:
                data = json.read(response.read())
            except json.ReadException, e:
                regex = re.compile('<span class="fielderror">(.*)</span>')
                match = regex.search(e.message)
                if match and len(match.groups()):
                    log.error(match.groups()[0])
                else:
                    log.error('Unexpected ReadException during request:' + e)
                raise ServerError, e.message
        except Exception, e:
            log.error('Error while parsing JSON data from server:', e)
            raise ServerError, str(e)

        return data
