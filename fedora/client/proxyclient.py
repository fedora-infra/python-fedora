# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2013  Red Hat, Inc.
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
'''Implement a class that sets up simple communication to a Fedora Service.

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. moduleauthor:: Ralph Bean <rbean@redhat.com>
'''

import copy
from hashlib import sha1
import logging
# For handling an exception that's coming from requests:
import ssl
import time
import warnings

from munch import munchify
from kitchen.text.converters import to_bytes
import requests
from six.moves import http_client as httplib
from six.moves import http_cookies as Cookie
from six.moves.urllib.parse import quote, urljoin, urlparse

from fedora import __version__
from fedora.client import AppError, AuthError, ServerError

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

    This class has several attributes.  These may be changed after
    instantiation however, please note that this class is intended to be
    threadsafe.  Changing these values when another thread may affect more
    than just the thread that you are making the change in.  (For instance,
    changing the debug option could cause other threads to start logging debug
    messages in the middle of a method.)

    .. attribute:: base_url

        Initial portion of the url to contact the server.  It is highly
        recommended not to change this value unless you know that no other
        threads are accessing this :class:`ProxyClient` instance.

    .. attribute:: useragent

        Changes the useragent string that is reported to the web server.

    .. attribute:: session_name

        Name of the cookie that holds the authentication value.

    .. attribute:: session_as_cookie

        If :data:`True`, then the session information is saved locally as
        a cookie.  This is here for backwards compatibility.  New code should
        set this to :data:`False` when constructing the :class:`ProxyClient`.

    .. attribute:: debug

        If :data:`True`, then more verbose logging is performed to aid in
        debugging issues.

    .. attribute:: insecure

        If :data:`True` then the connection to the server is not checked to be
        sure that any SSL certificate information is valid.  That means that
        a remote host can lie about who it is.  Useful for development but
        should not be used in production code.

    .. attribute:: retries

        Setting this to a positive integer will retry failed requests to the
        web server this many times.  Setting to a negative integer will retry
        forever.

    .. attribute:: timeout
        A float describing the timeout of the connection. The timeout only
        affects the connection process itself, not the downloading of the
        response body. Defaults to 120 seconds.

    .. versionchanged:: 0.3.33
        Added the timeout attribute
    '''
    log = log

    def __init__(self, base_url, useragent=None, session_name='tg-visit',
                 session_as_cookie=True, debug=False, insecure=False,
                 retries=None,
                 timeout=None):
        '''Create a client configured for a particular service.

        :arg base_url: Base of every URL used to contact the server

        :kwarg useragent: useragent string to use.  If not given, default to
            "Fedora ProxyClient/VERSION"
        :kwarg session_name: name of the cookie to use with session handling
        :kwarg session_as_cookie: If set to True, return the session as a
            SimpleCookie.  If False, return a session_id.  This flag allows us
            to maintain compatibility for the 0.3 branch.  In 0.4, code will
            have to deal with session_id's instead of cookies.
        :kwarg debug: If True, log debug information
        :kwarg insecure: If True, do not check server certificates against
            their CA's.  This means that man-in-the-middle attacks are
            possible against the `BaseClient`. You might turn this option on
            for testing against a local version of a server with a self-signed
            certificate but it should be off in production.
        :kwarg retries: if we get an unknown or possibly transient error from
            the server, retry this many times.  Setting this to a negative
            number makes it try forever.  Defaults to zero, no retries.
        :kwarg timeout: A float describing the timeout of the connection. The
            timeout only affects the connection process itself, not the
            downloading of the response body. Defaults to 120 seconds.

        .. versionchanged:: 0.3.33
            Added the timeout kwarg
        '''
        # Setup our logger
        self._log_handler = logging.StreamHandler()
        self.debug = debug
        format = logging.Formatter("%(message)s")
        self._log_handler.setFormatter(format)
        self.log.addHandler(self._log_handler)

        # When we are instantiated, go ahead and silence the python-requests
        # log.  It is kind of noisy in our app server logs.
        if not debug:
            requests_log = logging.getLogger("requests")
            requests_log.setLevel(logging.WARN)

        self.log.debug('proxyclient.__init__:entered')
        if base_url[-1] != '/':
            base_url = base_url + '/'
        self.base_url = base_url
        self.domain = urlparse(self.base_url).netloc
        self.useragent = useragent or 'Fedora ProxyClient/%(version)s' % {
            'version': __version__}
        self.session_name = session_name
        self.session_as_cookie = session_as_cookie
        if session_as_cookie:
            warnings.warn(
                'Returning cookies from send_request() is'
                ' deprecated and will be removed in 0.4.  Please port your'
                ' code to use a session_id instead by calling the ProxyClient'
                ' constructor with session_as_cookie=False',
                DeprecationWarning, stacklevel=2)
        self.insecure = insecure

        # Have to do retries and timeout default values this way as BaseClient
        # sends None for these values if not overridden by the user.
        if retries is None:
            self.retries = 0
        else:
            self.retries = retries
        if timeout is None:
            self.timeout = 120.0
        else:
            self.timeout = timeout
        self.log.debug('proxyclient.__init__:exited')

    def __get_debug(self):
        '''Return whether we have debug logging turned on.

        :Returns: True if debugging is on, False otherwise.
        '''
        if self._log_handler.level <= logging.DEBUG:
            return True
        return False

    def __set_debug(self, debug=False):
        '''Change debug level.

        :kwarg debug: A true value to turn debugging on, false value to turn it
            off.
        '''
        if debug:
            self.log.setLevel(logging.DEBUG)
            self._log_handler.setLevel(logging.DEBUG)
        else:
            self.log.setLevel(logging.ERROR)
            self._log_handler.setLevel(logging.INFO)

    debug = property(__get_debug, __set_debug, doc='''
    When True, we log extra debugging statements.  When False, we only log
    errors.
    ''')

    def send_request(self, method, req_params=None, auth_params=None,
                     file_params=None, retries=None, timeout=None):
        '''Make an HTTP request to a server method.

        The given method is called with any parameters set in ``req_params``.
        If auth is True, then the request is made with an authenticated session
        cookie.  Note that path parameters should be set by adding onto the
        method, not via ``req_params``.

        :arg method: Method to call on the server.  It's a url fragment that
            comes after the base_url set in __init__().  Note that any
            parameters set as extra path information should be listed here,
            not in ``req_params``.
        :kwarg req_params: dict containing extra parameters to send to the
            server
        :kwarg auth_params: dict containing one or more means of authenticating
            to the server.  Valid entries in this dict are:

            :cookie: **Deprecated** Use ``session_id`` instead.  If both
                ``cookie`` and ``session_id`` are set, only ``session_id`` will
                be used.  A ``Cookie.SimpleCookie`` to send as a session cookie
                to the server
            :session_id: Session id to put in a cookie to construct an identity
                for the server
            :username: Username to send to the server
            :password: Password to use with username to send to the server
            :httpauth: If set to ``basic`` then use HTTP Basic Authentication
                to send the username and password to the server.  This may be
                extended in the future to support other httpauth types than
                ``basic``.

            Note that cookie can be sent alone but if one of username or
            password is set the other must as well.  Code can set all of these
            if it wants and all of them will be sent to the server.  Be careful
            of sending cookies that do not match with the username in this
            case as the server can decide what to do in this case.
        :kwarg file_params: dict of files where the key is the name of the
            file field used in the remote method and the value is the local
            path of the file to be uploaded.  If you want to pass multiple
            files to a single file field, pass the paths as a list of paths.
        :kwarg retries: if we get an unknown or possibly transient error from
            the server, retry this many times.  Setting this to a negative
            number makes it try forever.  Default to use the :attr:`retries`
            value set on the instance or in :meth:`__init__`.
        :kwarg timeout: A float describing the timeout of the connection. The
            timeout only affects the connection process itself, not the
            downloading of the response body. Defaults to the :attr:`timeout`
            value set on the instance or in :meth:`__init__`.
        :returns: If ProxyClient is created with session_as_cookie=True (the
            default), a tuple of session cookie and data from the server.
            If ProxyClient was created with session_as_cookie=False, a tuple
            of session_id and data instead.
        :rtype: tuple of session information and data from server

        .. versionchanged:: 0.3.17
            No longer send tg_format=json parameter.  We rely solely on the
            Accept: application/json header now.
        .. versionchanged:: 0.3.21
            * Return data as a Bunch instead of a DictContainer
            * Add file_params to allow uploading files
        .. versionchanged:: 0.3.33
            Added the timeout kwarg
        '''
        self.log.debug('proxyclient.send_request: entered')

        # parameter mangling
        file_params = file_params or {}

        # Check whether we need to authenticate for this request
        session_id = None
        username = None
        password = None
        if auth_params:
            if 'session_id' in auth_params:
                session_id = auth_params['session_id']
            elif 'cookie' in auth_params:
                warnings.warn(
                    'Giving a cookie to send_request() to'
                    ' authenticate is deprecated and will be removed in 0.4.'
                    ' Please port your code to use session_id instead.',
                    DeprecationWarning, stacklevel=2)
                session_id = auth_params['cookie'].output(attrs=[],
                                                          header='').strip()
            if 'username' in auth_params and 'password' in auth_params:
                username = auth_params['username']
                password = auth_params['password']
            elif 'username' in auth_params or 'password' in auth_params:
                raise AuthError('username and password must both be set in'
                                ' auth_params')
            if not (session_id or username):
                raise AuthError(
                    'No known authentication methods'
                    ' specified: set "cookie" in auth_params or set both'
                    ' username and password in auth_params')

        # urljoin is slightly different than os.path.join().  Make sure method
        # will work with it.
        method = method.lstrip('/')
        # And join to make our url.
        url = urljoin(self.base_url, quote(method))

        data = None     # decoded JSON via json.load()

        # Set standard headers
        headers = {
            'User-agent': self.useragent,
            'Accept': 'application/json',
        }

        # Files to upload
        for field_name, local_file_name in file_params:
            file_params[field_name] = open(local_file_name, 'rb')

        cookies = requests.cookies.RequestsCookieJar()
        # If we have a session_id, send it
        if session_id:
            # Anytime the session_id exists, send it so that visit tracking
            # works.  Will also authenticate us if there's a need.  Note that
            # there's no need to set other cookie attributes because this is a
            # cookie generated client-side.
            cookies.set(self.session_name, session_id)

        complete_params = req_params or {}
        if session_id:
            # Add the csrf protection token
            token = sha1(to_bytes(session_id))
            complete_params.update({'_csrf_token': token.hexdigest()})

        auth = None
        if username and password:
            if auth_params.get('httpauth', '').lower() == 'basic':
                # HTTP Basic auth login
                auth = (username, password)
            else:
                # TG login
                # Adding this to the request data prevents it from being
                # logged by apache.
                complete_params.update({
                    'user_name': to_bytes(username),
                    'password': to_bytes(password),
                    'login': 'Login',
                })

        # If debug, give people our debug info
        self.log.debug('Creating request %(url)s' %
                       {'url': to_bytes(url)})
        self.log.debug('Headers: %(header)s' %
                       {'header': to_bytes(headers, nonstring='simplerepr')})
        if self.debug and complete_params:
            debug_data = copy.deepcopy(complete_params)

            if 'password' in debug_data:
                debug_data['password'] = 'xxxxxxx'

            self.log.debug('Data: %r' % debug_data)

        if retries is None:
            retries = self.retries

        if timeout is None:
            timeout = self.timeout

        num_tries = 0
        while True:
            try:
                response = requests.post(
                    url,
                    data=complete_params,
                    cookies=cookies,
                    headers=headers,
                    auth=auth,
                    verify=not self.insecure,
                    timeout=timeout,
                )
            except (requests.Timeout, requests.exceptions.SSLError) as e:
                if isinstance(e, requests.exceptions.SSLError):
                    # And now we know how not to code a library exception
                    # hierarchy...  We're expecting that requests is raising
                    # the following stupidity:
                    # requests.exceptions.SSLError(
                    #   urllib3.exceptions.SSLError(
                    #     ssl.SSLError('The read operation timed out')))
                    # If we weren't interested in reraising the exception with
                    # full tracdeback we could use a try: except instead of
                    # this gross conditional.  But we need to code defensively
                    # because we don't want to raise an unrelated exception
                    # here and if requests/urllib3 can do this sort of
                    # nonsense, they may change the nonsense in the future
                    #
                    # And a note on the __class__.__name__/__module__ parsing:
                    # On top of all the other things it does wrong, requests
                    # is bundling a copy of urllib3.  Distros can unbundle it.
                    # But because of the bundling, python will think
                    # exceptions raised by the version downloaded by pypi
                    # (requests.packages.urllib3.exceptions.SSLError) are
                    # different than the exceptions raised by the unbundled
                    # distro version (urllib3.exceptions.SSLError).  We could
                    # do a try: except trying to import both of these
                    # SSLErrors and then code to detect either one of them but
                    # the whole thing is just stupid.  So we'll use a stupid
                    # hack of our own that (1) means we don't have to depend
                    # on urllib3 just for this exception and (2) is (slightly)
                    # less likely to break on the whims of the requests
                    # author.
                    if not (e.args
                            and e.args[0].__class__.__name__ == 'SSLError'
                            and e.args[0].__class__.__module__.endswith(
                                'urllib3.exceptions')
                            and e.args[0].args
                            and isinstance(e.args[0].args[0], ssl.SSLError)
                            and e.args[0].args[0].args
                            and 'timed out' in e.args[0].args[0].args[0]):
                        # We're only interested in timeouts here
                        raise
                self.log.debug('Request timed out')
                if retries < 0 or num_tries < retries:
                    num_tries += 1
                    self.log.debug(
                        'Attempt #%(try)s failed' % {'try': num_tries})
                    time.sleep(0.5)
                    continue
                # Fail and raise an error
                # Raising our own exception protects the user from the
                # implementation detail of requests vs pycurl vs urllib
                raise ServerError(
                    url, -1, 'Request timed out after %s seconds' % timeout)

            # When the python-requests module gets a response, it attempts to
            # guess the encoding using chardet (or a fork)
            # That process can take an extraordinarily long time for long
            # response.text strings.. upwards of 30 minutes for FAS queries to
            # /accounts/user/list JSON api!  Therefore, we cut that codepath
            # off at the pass by assuming that the response is 'utf-8'.  We can
            # make that assumption because we're only interfacing with servers
            # that we run (and we know that they all return responses
            # encoded 'utf-8').
            response.encoding = 'utf-8'

            # Check for auth failures
            # Note: old TG apps returned 403 Forbidden on authentication
            # failures.
            # Updated apps return 401 Unauthorized
            # We need to accept both until all apps are updated to return 401.
            http_status = response.status_code
            if http_status in (401, 403):
                # Wrong username or password
                self.log.debug('Authentication failed logging in')
                raise AuthError(
                    'Unable to log into server.  Invalid'
                    ' authentication tokens.  Send new username and password')
            elif http_status >= 400:
                if retries < 0 or num_tries < retries:
                    # Retry the request
                    num_tries += 1
                    self.log.debug(
                        'Attempt #%(try)s failed' % {'try': num_tries})
                    time.sleep(0.5)
                    continue
                # Fail and raise an error
                try:
                    msg = httplib.responses[http_status]
                except (KeyError, AttributeError):
                    msg = 'Unknown HTTP Server Response'
                raise ServerError(url, http_status, msg)
            # Successfully returned data
            break

        # In case the server returned a new session cookie to us
        new_session = response.cookies.get(self.session_name, '')

        try:
            data = response.json()
        except ValueError as e:
            # The response wasn't JSON data
            raise ServerError(
                url, http_status, 'Error returned from'
                ' json module while processing %(url)s: %(err)s' %
                {'url': to_bytes(url), 'err': to_bytes(e)})

        if 'exc' in data:
            name = data.pop('exc')
            message = data.pop('tg_flash')
            raise AppError(name=name, message=message, extras=data)

        # If we need to return a cookie for deprecated code, convert it here
        if self.session_as_cookie:
            cookie = Cookie.SimpleCookie()
            cookie[self.session_name] = new_session
            new_session = cookie

        self.log.debug('proxyclient.send_request: exited')
        data = munchify(data)
        return new_session, data

__all__ = (ProxyClient,)
