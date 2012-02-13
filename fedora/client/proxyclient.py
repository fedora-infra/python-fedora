# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011  Red Hat, Inc.
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
'''

import Cookie
import re
import urllib
import httplib
import pycurl
import logging
import time
import warnings
from urlparse import urljoin

try:
    import simplejson as json
except ImportError:
    import json as json

try:
    from hashlib import sha1 as sha_constructor
except ImportError:
    from sha import new as sha_constructor

from bunch import bunchify
from kitchen.iterutils import isiterable
from kitchen.text.converters import to_bytes

from fedora import __version__, b_
from fedora.client import AppError, AuthError, ServerError

log = logging.getLogger(__name__)

class _PyCurlData(object):
    def __init__(self):
        self._data = []

    def write_data(self, buf):
        self._data.append(buf)

    def _read_data(self):
        return ''.join(self._data)

    def _clear_data(self):
        self._data = []

    data = property(_read_data, write_data, _clear_data)

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
    '''
    log = log

    def __init__(self, base_url, useragent=None, session_name='tg-visit',
            session_as_cookie=True, debug=False, insecure=False, retries=0):
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

        '''
        # Setup our logger
        self._log_handler = logging.StreamHandler()
        self.debug = debug
        format = logging.Formatter("%(message)s")
        self._log_handler.setFormatter(format)
        self.log.addHandler(self._log_handler)

        self.log.debug(b_('proxyclient.__init__:entered'))
        if base_url[-1] != '/':
            base_url = base_url +'/'
        self.base_url = base_url
        self.useragent = useragent or 'Fedora ProxyClient/%(version)s' % {
                'version': __version__}
        self.session_name = session_name
        self.session_as_cookie = session_as_cookie
        if session_as_cookie:
            warnings.warn(b_('Returning cookies from send_request() is'
                ' deprecated and will be removed in 0.4.  Please port your'
                ' code to use a session_id instead by calling the ProxyClient'
                ' constructor with session_as_cookie=False'),
                DeprecationWarning, stacklevel=2)
        self.insecure = insecure
        self.retries = retries or 0
        self.log.debug(b_('proxyclient.__init__:exited'))

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
            file_params=None, retries=None):
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
            number makes it try forever.  Defaults to zero, no retries.
            number makes it try forever.  Default to use the :attr:`retries`
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
        '''
        self.log.debug(b_('proxyclient.send_request: entered'))
        # Check whether we need to authenticate for this request
        session_id = None
        username = None
        password = None
        if auth_params:
            if 'session_id' in auth_params:
                session_id = auth_params['session_id']
            elif 'cookie' in auth_params:
                warnings.warn(b_('Giving a cookie to send_request() to'
                ' authenticate is deprecated and will be removed in 0.4.'
                ' Please port your code to use session_id instead.'),
                DeprecationWarning, stacklevel=2)
                session_id = auth_params['cookie'].output(attrs=[],
                        header='').strip()
            if 'username' in auth_params and 'password' in auth_params:
                username = auth_params['username']
                password = auth_params['password']
            elif 'username' in auth_params or 'password' in auth_params:
                raise AuthError(b_('username and password must both be set in'
                        ' auth_params'))
            if not (session_id or username):
                raise AuthError(b_('No known authentication methods'
                    ' specified: set "cookie" in auth_params or set both'
                    ' username and password in auth_params'))

        # urljoin is slightly different than os.path.join().  Make sure method
        # will work with it.
        method = method.lstrip('/')
        # And join to make our url.
        url = urljoin(self.base_url, urllib.quote(method))

        response = _PyCurlData() # The data we get back from the server
        data = None     # decoded JSON via json.load()

        request = pycurl.Curl()
        # Fix encoding issue related to pycurl bug#1831680
        request.setopt(pycurl.URL, to_bytes(url))
        # Boilerplate so pycurl processes cookies
        request.setopt(pycurl.COOKIEFILE, '/dev/null')
        # Associate with the response to accumulate data
        request.setopt(pycurl.WRITEFUNCTION, response.write_data)
        # Follow redirect
        request.setopt(pycurl.FOLLOWLOCATION, True)
        request.setopt(pycurl.MAXREDIRS, 5)
        if self.insecure:
            # Don't check that the server certificate is valid
            # This flag should really only be set for debugging
            request.setopt(pycurl.SSL_VERIFYPEER, False)
            request.setopt(pycurl.SSL_VERIFYHOST, False)

        # Set standard headers
        headers = ['User-agent: %s' % self.useragent,
                'Accept: application/json']
        request.setopt(pycurl.HTTPHEADER, headers)

        # Files to upload
        if file_params:
            # pycurl wants files to be uploaded in a specific format.  That
            # format is:
            #
            # [(file form field name, [(FORM_FILE, 'file local path'), ]),
            #  (file form field name2, [(FORM_FILE, 'file2 local path'), ])
            # ]
            file_data = []
            for field_name, field_value in file_params.iteritems():
                files = []
                if isiterable(field_value):
                    for filename in field_value:
                        files.append((pycurl.FORM_FILE, filename))
                else:
                    files = [(pycurl.FORM_FILE, field_value)]
                file_data.append((field_name, files))
            request.setopt(pycurl.HTTPPOST, file_data)

        # If we have a session_id, send it
        if session_id:
            # Anytime the session_id exists, send it so that visit tracking
            # works.  Will also authenticate us if there's a need.
            request.setopt(pycurl.COOKIE, to_bytes('%s=%s;' % (self.session_name,
                session_id)))

        complete_params = req_params or {}
        if session_id:
            # Add the csrf protection token
            token = sha_constructor(session_id)
            complete_params.update({'_csrf_token': token.hexdigest()})
        if username and password:
            if auth_params.get('httpauth', '').lower() == 'basic':
                # HTTP Basic auth login
                userpwd = '%s:%s' % (to_bytes(username), to_bytes(password))
                request.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
                request.setopt(pycurl.USERPWD, userpwd)
            else:
                # TG login
                # Adding this to the request data prevents it from being logged by
                # apache.
                complete_params.update({'user_name': to_bytes(username),
                        'password': to_bytes(password), 'login': 'Login'})

        req_data = None
        if complete_params:
            # set None params to empty string otherwise the string 'None' gets
            # sent.
            for i in complete_params.iteritems():
                if i[1] is None:
                    complete_params[i[0]] = ''
            req_data = urllib.urlencode(complete_params, doseq=True)
            request.setopt(pycurl.POSTFIELDS, req_data)

        # If debug, give people our debug info
        self.log.debug(b_('Creating request %(url)s') %
                {'url': to_bytes(url)})
        self.log.debug(b_('Headers: %(header)s') %
                {'header': to_bytes(headers, nonstring='simplerepr')})
        if self.debug and req_data:
            debug_data = re.sub(r'(&?)password[^&]+(&?)',
                    '\g<1>password=xxxxxxx\g<2>', req_data)
            self.log.debug(b_('Data: %(data)s') %
                    {'data': to_bytes(debug_data)})

        num_tries = 0
        if retries is None:
            retries = self.retries
        while True:
            # run the request
            request.perform()

            # Check for auth failures
            # Note: old TG apps returned 403 Forbidden on authentication failures.
            # Updated apps return 401 Unauthorized
            # We need to accept both until all apps are updated to return 401.
            http_status = request.getinfo(pycurl.HTTP_CODE)
            if http_status in (401, 403):
                # Wrong username or password
                self.log.debug(b_('Authentication failed logging in'))
                raise AuthError(b_('Unable to log into server.  Invalid'
                        ' authentication tokens.  Send new username and password'))
            elif http_status >= 400:
                if retries < 0 or num_tries < retries:
                    # Retry the request
                    num_tries += 1
                    self.log.debug(b_('Attempt #%(try)s failed') % {'try': num_tries})
                    time.sleep(0.5)
                    continue
                # Fail and raise an error
                try:
                    msg = httplib.responses[http_status]
                except (KeyError, AttributeError):
                    msg = b_('Unknown HTTP Server Response')
                raise ServerError(url, http_status, msg)
            # Successfully returned data
            break

        # In case the server returned a new session cookie to us
        new_session = ''
        cookies = request.getinfo(pycurl.INFO_COOKIELIST)
        for cookie in cookies:
            host, isdomain, path, secure, expires, name, value  = \
                    cookie.split('\t')
            if name == self.session_name:
                new_session = value
                break

        # Read the response
        json_string = response.data

        try:
            data = json.loads(json_string)
        except ValueError, e:
            # The response wasn't JSON data
            raise ServerError(url, http_status, b_('Error returned from'
                    ' json module while processing %(url)s: %(err)s') %
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

        request.close()
        self.log.debug(b_('proxyclient.send_request: exited'))
        data = bunchify(data)
        return new_session, data

__all__ = (ProxyClient,)
