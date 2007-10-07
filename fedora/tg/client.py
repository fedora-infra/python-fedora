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

'''
python-fedora, python module to interact with Fedora Infrastructure Services
'''

import Cookie
import urllib
import urllib2
import logging
import cPickle as pickle
import re
import inspect
import simplejson
from os import path

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
    def __init__(self, baseURL, username=None, password=None, debug=False):
        self.baseURL = baseURL
        self.username = username
        self.password = password
        self._sessionCookie = None

        # Setup our logger
        sh = logging.StreamHandler()
        if debug:
            log.setLevel(logging.DEBUG)
            sh.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.INFO)
            sh.setLevel(logging.INFO)
        format = logging.Formatter("%(message)s")
        sh.setFormatter(format)
        log.addHandler(sh)

        self._load_session()
        if username and password:
            self._authenticate()

    def _authenticate(self, force=False):
        '''
            Return an authenticated session cookie.
        '''
        if not force and self._sessionCookie:
            return self._sessionCookie

        if not self.username:
            raise AuthError, 'username must be set'
        if not self.password:
            raise AuthError, 'password must be set'

        req = urllib2.Request(self.baseURL + '/login?tg_format=json')
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
            else:
                raise

        loginData = simplejson.load(loginPage)

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
        save = {self.username : self._sessionCookie}
        pickle.dump(save, sessionFile)
        sessionFile.close()

    def _load_session(self):
        '''
            Load a stored session cookie.
        '''
        if path.isfile(SESSION_FILE):
            sessionFile = file(SESSION_FILE, 'r')
            try:
                savedSession = pickle.load(sessionFile)
                self._sessionCookie = savedSession[self.username]
                log.debug('Loaded session %s' % self._sessionCookie)
            except EOFError:
                log.error('Unable to load session from %s' % SESSION_FILE)
            except KeyError:
                log.debug('Session is for a different user')
            sessionFile.close()

    def send_request(self, method, auth=False, input=None):
        '''
            Send a request to the server.  The given method is called with any
            keyword parameters in **kw.  If auth is True, then the request is
            made with an authenticated session cookie.
        '''
        url = self.baseURL + method + '/?tg_format=json'

        response = None # the JSON that we get back from the server
        data = None     # decoded JSON via simplejson.load()

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

        if 'logging_in' in data:
            if (inspect.currentframe().f_back.f_code !=
                    inspect.currentframe().f_code):
                self._authenticate(force=True)
                data = self.send_request(method, auth, input)
            else:
                # We actually shouldn't ever reach here.  Unless something goes
                # drastically wrong _authenticate should raise an AuthError
                raise AuthError, 'Unable to log into server: %s' % (
                        data['message'],)
        return data
