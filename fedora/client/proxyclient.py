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
'''Implement a class that sets up simple communication to a Fedora Service.'''

import Cookie
import re
import urllib
import urllib2
import logging
import simplejson
import warnings
from urlparse import urljoin
from fedora import __version__
from fedora import _

from fedora.client import AuthError, ServerError, AppError, DictContainer

log = logging.getLogger(__name__)

class ProxyClient(object):
    # pylint: disable-msg=R0903
    '''
    A client to a Fedora Service.  This class is optimized to proxy multiple
    users to a service.  ProxyClient is designed to be threadsafe so that
    code can instantiate one instance of the class and use it for multiple
    requests for different users from different threads.

    If you want something that can manage one user's connection to a Fedora
    Service, then look into using BaseClient instead.
    '''
    def __init__(self, base_url, useragent=None, session_name='tg-visit',
            session_as_cookie=True, debug=False):
        '''Create a client configured for a particular service.

        Arguments:
        :base_url: Base of every URL used to contact the server

        Keyword Arguments:
        :useragent: useragent string to use.  If not given, default to
            "Fedora ProxyClient/VERSION"
        :session_name: name of the cookie to use with session handling
        :session_as_cookie: If set to True, return the session as a
            SimpleCookie.  If False, return a session_id.  This flag allows us
            to maintain compatibility for the 0.3 branch.  In 0.4, code will
            have to deal with session_id's instead of cookies.
        :debug: If True, log debug information
        '''
        # Setup our logger
        self._log_handler = logging.StreamHandler()
        self.debug = debug
        format = logging.Formatter("%(message)s")
        self._log_handler.setFormatter(format)
        log.addHandler(self._log_handler)

        log.debug('proxyclient.__init__:entered')
        if base_url[-1] != '/':
            base_url = base_url +'/'
        self.base_url = base_url
        self.useragent = useragent or 'Fedora ProxyClient/%(version)s' % {
                'version': __version__}
        self.session_name = session_name
        self.session_as_cookie = session_as_cookie
        if session_as_cookie:
            warnings.warn(_("Returning cookies from send_request() is"
                " deprecated and will be removed in 0.4.  Please port your"
                " code to use a sesison_id instead by calling the ProxyClient"
                " constructor with session_as_cookie=False"),
                DeprecationWarning, stacklevel=2)
        log.debug('proxyclient.__init__:exited')

    def __get_debug(self):
        '''Return whether we have debug logging turned on.
        '''
        if self._log_handler.level <= logging.DEBUG:
            return True
        return False

    def __set_debug(self, debug=False):
        '''Change debug level.'''
        if debug:
            log.setLevel(logging.DEBUG)
            self._log_handler.setLevel(logging.DEBUG)
        else:
            log.setLevel(logging.ERROR)
            self._log_handler.setLevel(logging.INFO)

    debug = property(__get_debug, __set_debug, doc='''
    When True, we log extra debugging statements.  When False, we only log
    errors.
    ''')

    def send_request(self, method, req_params=None, auth_params=None):
        '''Make an HTTP request to a server method.

        The given method is called with any parameters set in req_params.  If
        auth is True, then the request is made with an authenticated session
        cookie.  Note that path parameters should be set by adding onto the
        method, not via ``req_params``.

        Arguments:
        :method: Method to call on the server.  It's a url fragment that comes
            after the base_url set in __init__().  Note that any parameters set
            as extra path information should be listed here, not in req_params.

        Keyword Arguments:
        :req_params: dict containing extra parameters to send to the server.
        :auth_params: dict containing one or more means of authenticating to
            the server.  Valid entries in this dict are:
            :cookie: *Deprecated* Use session_id instead.  If both cookie and
                session_id are set, only session_id will be used.
                A Cookie.SimpleCookie to send as a session cookie to the server
            :session_id: Session id to put in a cookie to construct an identity
                for the server.
            :username: Username to send to the server.
            :password: Password to use with username to send to the server.
            Note that cookie can be sent alone but if one of username or
            password is set the other must as well.  Code can set all of these
            if it wants and all of them will be sent to the server.  Be careful
            of sending cookies that do not match with the username in this
            case as the server can decide what to do in this case.

        Returns: a tuple of session cookie and data returned from the server.
                 If ProxyClient was created with session_as_cookie=False, return
                 a tuple of session_id and data instead.
        '''
        log.debug('proxyclient.send_request: entered')
        # Check whether we need to authenticate for this request
        session_cookie = None
        username = None
        password = None
        if auth_params:
            if 'session_id' in auth_params:
                session_cookie = Cookie.SimpleCookie()
                session_cookie[self.session_name] = auth_params['session_id']
            elif 'cookie' in auth_params:
                warnings.warn(_("Giving a cookie to send_request() to"
                " authenticate is deprecated and will be removed in 0.4."
                " Please port your code to use session_id instead."
                DeprecationWarning, stacklevel=2)
                session_cookie = auth_params['cookie']
            if 'username' in auth_params and 'password' in auth_params:
                username = auth_params['username']
                password = auth_params['password']
            elif 'username' in auth_params or 'password' in auth_params:
                raise AuthError, _('username and password must both be set in'
                        ' auth_params')
            if not (session_cookie or username):
                raise AuthError, _('No known authentication methods specified:'
                        ' set "cookie" in auth_params or set both username and'
                        ' password in auth_params')

        # urljoin is slightly different than os.path.join().  Make sure method
        # will work with it.
        method = method.lstrip('/')
        # And join to make our url.
        # Note: ?tg_format=json is going away in the future as the Accept
        # header should serve the same purpose in a more framework neutral
        # manner.
        url = urljoin(self.base_url, urllib.quote(method) + '?tg_format=json')

        response = None # the JSON that we get back from the server
        data = None     # decoded JSON via simplejson.load()

        req = urllib2.Request(url)
        req.add_header('User-agent', self.useragent)
        req.add_header('Accept', 'text/javascript')

        complete_params = {}
        if req_params:
            complete_params = req_params
        if username and password:
            # Adding this to the request data prevents it from being logged by
            # apache.
            complete_params.update({'user_name': username,
                    'password': password, 'login': 'Login'})
        if complete_params:
            req.add_data(urllib.urlencode(complete_params, doseq=True))

        if session_cookie:
            # Anytime the cookie exists, send it so that visit tracking works.
            # Will also authenticate us if there's a need.
            req.add_header('Cookie', session_cookie.output(attrs=[],
                header='').strip())

        log.debug(_('Creating request %(url)s') % {'url': req.get_full_url()})
        log.debug(_('Headers: %(header)s') % {'header': req.headers})
        if self.debug and req.data:
            debug_data = re.sub(r'(&?)password[^&]+(&?)',
                    '\g<1>password=XXXX\g<2>', req.data)
            log.debug(_('Data: %(data)s') % {'data': debug_data})

        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            if e.msg == 'Forbidden':
                # Wrong username or password
                log.debug(e)
                raise AuthError, _('Unable to log into server.  Invalid'
                        ' authentication tokens.  Send new username and'
                        ' password:  %(error)s') % {'error': str(e)}
            else:
                raise

        # In case the server returned a new session cookie to us
        new_session_cookie = Cookie.SimpleCookie()
        try:
            new_session_cookie.load(response.headers['set-cookie'])
        except (KeyError, AttributeError): # pylint: disable-msg=W0704
            # It's okay if the server didn't send a new cookie
            pass
        if self.session_as_cookie:
            new_session = new_session_cookie
        else:
            # Retrieve the session id from the cookie
            new_session = new_session_cookie.get(self.session_name, '')
            if new_session:
                new_session = new_session.value()

        # Read the response
        json_string = response.read()
        try:
            data = simplejson.loads(json_string)
        except ValueError, e:
            # The response wasn't JSON data
            raise ServerError, 'Error returned from simplejson while' \
                    ' processing %s: %s' % (url, str(e))

        if 'exc' in data:
            raise AppError(name = data['exc'], message = data['tg_flash'])

        log.debug('proxyclient.send_request: exited')
        return new_session, DictContainer(data)
