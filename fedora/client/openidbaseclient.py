#!/usr/bin/env python2 -tt
# -*- coding: utf-8 -*-
#
# Copyright (C) 2013-2015  Red Hat, Inc.
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

"""Base client for application relying on OpenID for authentication.

.. moduleauthor:: Pierre-Yves Chibon <pingou@fedoraproject.org>
.. moduleauthor:: Toshio Kuratomi <toshio@fedoraproject.org>
.. moduleauthor:: Ralph Bean <rbean@redhat.com>

.. versionadded: 0.3.35

"""

# :F0401: Unable to import : Disabled because these will either import on py3
#   or py2 not both.
# :E0611: No name $X in module: This was renamed in python3

import json
import logging
import time
import os

# pylint: disable-msg=F0401
try:
    # pylint: disable-msg=E0611
    # Python 3
    from urllib.parse import urljoin
except ImportError:
    # Python 2
    from urlparse import urljoin
# pylint: enable-msg=F0401,E0611


import lockfile
import requests
from functools import wraps
from munch import munchify
from kitchen.text.converters import to_bytes

from fedora import __version__
from fedora.client import AuthError, LoginRequiredError, ServerError
from fedora.client.openidproxyclient import (
    OpenIdProxyClient, absolute_url, openid_login)

log = logging.getLogger(__name__)

b_SESSION_DIR = os.path.join(os.path.expanduser('~'), '.fedora')
b_SESSION_FILE = os.path.join(b_SESSION_DIR, 'openidbaseclient-sessions.cache')


def requires_login(func):
    """
    Decorator function for get or post requests requiring login.

    Decorate a controller method that requires the user to be authenticated.
    Example::

        from fedora.client.openidbaseclient import requires_login

        @requires_login
        def rename_user(new_name):
            user = new_name
            # [...]
    """
    def _decorator(request, *args, **kwargs):
        """ Run the function and check if it redirected to the openid form.
        Or if we got a 403
        """
        output = func(request, *args, **kwargs)
        if output and \
                '<title>OpenID transaction in progress</title>' in output.text:
            raise LoginRequiredError(
                '{0} requires a logged in user'.format(output.url))
        elif output and output.status_code == 403:
            raise LoginRequiredError(
                '{0} requires a logged in user'.format(output.url))
        return output
    return wraps(func)(_decorator)


class OpenIdBaseClient(OpenIdProxyClient):

    """ A client for interacting with web services relying on openid auth. """

    def __init__(self, base_url, login_url=None, useragent=None, debug=False,
                 insecure=False, openid_insecure=False, username=None,
                 cache_session=True, retries=None, timeout=None):
        """Client for interacting with web services relying on fas_openid auth.

        :arg base_url: Base of every URL used to contact the server
        :kwarg login_url: The url to the login endpoint of the application.
            If none are specified, it uses the default `/login`.
        :kwarg useragent: Useragent string to use.  If not given, default to
            "Fedora OpenIdBaseClient/VERSION"
        :kwarg debug: If True, log debug information
        :kwarg insecure: If True, do not check server certificates against
            their CA's.  This means that man-in-the-middle attacks are
            possible against the `BaseClient`. You might turn this option on
            for testing against a local version of a server with a self-signed
            certificate but it should be off in production.
        :kwarg openid_insecure: If True, do not check the openid server
            certificates against their CA's.  This means that man-in-the-
            middle attacks are possible against the `BaseClient`. You might
            turn this option on for testing against a local version of a
            server with a self-signed certificate but it should be off in
            production.
        :kwarg username: Username for establishing authenticated connections
        :kwarg cache_session: If set to true, cache the user's session data on
            the filesystem between runs
        :kwarg retries: if we get an unknown or possibly transient error from
            the server, retry this many times.  Setting this to a negative
            number makes it try forever.  Defaults to zero, no retries.
        :kwarg timeout: A float describing the timeout of the connection. The
            timeout only affects the connection process itself, not the
            downloading of the response body. Defaults to 120 seconds.

        """

        # These are also needed by OpenIdProxyClient
        self.useragent = useragent or 'Fedora BaseClient/%(version)s' % {
            'version': __version__}
        self.base_url = base_url
        self.login_url = login_url or urljoin(self.base_url, '/login')
        self.debug = debug
        self.insecure = insecure
        self.openid_insecure = openid_insecure
        self.retries = retries
        self.timeout = timeout

        # These are specific to OpenIdBaseClient
        self.username = username
        self.cache_session = cache_session
        self.cache_lock = lockfile.FileLock(b_SESSION_FILE)

        # Make sure the database for storing the session cookies exists
        if cache_session:
            self._initialize_session_cache()

        # python-requests session.  Holds onto cookies
        self._session = requests.session()
        # See if we have any cookies kicking around from a previous run
        self._load_cookies()

    def _initialize_session_cache(self):
        # Note -- fallback to returning None on any problems as this isn't
        # critical.  It just makes it so that we don't have to ask the user
        # for their password over and over.
        if not os.path.isdir(b_SESSION_DIR):
            try:
                os.makedirs(b_SESSION_DIR, mode=0o755)
            except OSError as err:
                log.warning('Unable to create {file}: {error}'.format(
                    file=b_SESSION_DIR, error=err))
                self.cache_session = False
                return None

    @requires_login
    def _authed_post(self, url, params=None, data=None, **kwargs):
        """ Return the request object of a post query."""
        response = self._session.post(url, params=params, data=data, **kwargs)
        return response

    @requires_login
    def _authed_get(self, url, params=None, data=None, **kwargs):
        """ Return the request object of a get query."""
        response = self._session.get(url, params=params, data=data, **kwargs)
        return response

    def send_request(self, method, auth=False, verb='POST', retries=None,
                     retry_sleep=None, **kwargs):
        """Make an HTTP request to a server method.

        The given method is called with any parameters set in req_params.  If
        auth is True, then the request is made with an authenticated session
        cookie.

        :arg method: Method to call on the server.  It's a url fragment that
            comes after the :attr:`base_url` set in :meth:`__init__`.
        :kwarg retries: if we get an unknown or possibly transient error from
            the server, retry this many times.  Setting this to a negative
            number makes it try forever.  Default to use the :attr:`retries`
            value set on the instance or in :meth:`__init__` (which defaults
            to zero, no retries).
        :kwarg timeout: A float describing the timeout of the connection. The
            timeout only affects the connection process itself, not the
            downloading of the response body. Default to use the
            :attr:`timeout` value set on the instance or in :meth:`__init__`
            (which defaults to 120s).
        :kwarg auth: If True perform auth to the server, else do not.
        :kwarg req_params: Extra parameters to send to the server.
        :kwarg file_params: dict of files where the key is the name of the
            file field used in the remote method and the value is the local
            path of the file to be uploaded.  If you want to pass multiple
            files to a single file field, pass the paths as a list of paths.
        :kwarg verb: HTTP verb to use.  GET and POST are currently supported.
            POST is the default.
        :kwarg retries: if we get an unknown or possibly transient error
            from the server, retry this many times.  Setting this to a
            negative number makes it try forever.  Default to use the
            :attr:`retries` value set on the instance or in :meth:`__init__`.
        :kwarg retry_sleep: the time (in second) to wait between retries.
            Defaults to `None` in which cases in uses the inherited `0.5`
            second value.

        """
        # Decide on the set of auth cookies to use

        method = absolute_url(self.base_url, method)

        self._authed_verb_dispatcher = {(False, 'POST'): self._session.post,
                                        (False, 'GET'): self._session.get,
                                        (True, 'POST'): self._authed_post,
                                        (True, 'GET'): self._authed_get}
        try:
            func = self._authed_verb_dispatcher[(auth, verb)]
        except KeyError:
            raise Exception('Unknown HTTP verb')

        if retries is None:
            retries = self.retries

        if timeout is None:
            timeout = self.timeout

        retry_sleep = retry_sleep if retry_sleep is not None else self.retry_sleep

        num_tries = 0
        while True:
            try:
                output = func(method, **kwargs)
            except LoginRequiredError:
                raise AuthError('Unable to log into server.')

            # When the python-requests module gets a response, it attempts
            # to guess the encoding using chardet (or a fork)
            # That process can take an extraordinarily long time for long
            # response.text strings.. upwards of 30 minutes for FAS queries
            # to /accounts/user/list JSON api!  Therefore, we cut that
            # codepath off at the pass by assuming that the response is
            # 'utf-8'.  We can make that assumption because we're only
            # interfacing with servers that we run (and we know that they
            # all return responses encoded 'utf-8').
            response.encoding = 'utf-8'

            http_status = response.status_code
            if http_status == 401:
                # Wrong token or username or password
                log.debug('Authentication failed logging in')
                raise AuthError('Unable to log into server.')
            elif http_status >= 500:
                if retries < 0 or num_tries < retries:
                    # Retry the request
                    num_tries += 1
                    log.debug('Attempt #%s failed', num_tries)
                    time.sleep(retry_sleep)
                    continue
                # Fail and raise an error
                try:
                    msg = httplib.responses[http_status]
                except (KeyError, AttributeError):
                    msg = 'Unknown HTTP Server Response'
                raise ServerError(url, http_status, msg)

            try:
                data = output.json
                # Compatibility with newer python-requests
                if callable(data):
                    data = data()
            except (requests.Timeout, requests.exceptions.SSLError) as err:
                if isinstance(err, requests.exceptions.SSLError):
                    # And now we know how not to code a library exception
                    # hierarchy...  We're expecting that requests is raising
                    # the following stupidity:
                    # requests.exceptions.SSLError(
                    #   urllib3.exceptions.SSLError(
                    #     ssl.SSLError('The read operation timed out')))
                    # If we weren't interested in reraising the exception with
                    # full traceback we could use a try: except instead of
                    # this gross conditional.  But we need to code defensively
                    # because we don't want to raise an unrelated exception
                    # here and if requests/urllib3 can do this sort of
                    # nonsense, they may change the nonsense in the future
                    if not (err.args and isinstance(
                                err.args[0], urllib3.exceptions.SSLError)
                            and err.args[0].args
                            and isinstance(err.args[0].args[0], ssl.SSLError)
                            and err.args[0].args[0].args
                            and 'timed out' in err.args[0].args[0].args[0]):
                        # We're only interested in timeouts here
                        raise
                log.debug('Request timed out')
                if retries < 0 or num_tries < retries:
                    num_tries += 1
                    log.debug('Attempt #%s failed', num_tries)
                    time.sleep(retry_sleep)
                    continue
                # Fail and raise an error
                # Raising our own exception protects the user from the
                # implementation detail of requests vs pycurl vs urllib
                raise ServerError(
                    method,
                    -1,
                    'Request timed out after %s seconds' % timeout)

            except ValueError as e:
                # The response wasn't JSON data
                raise ServerError(
                    method, output.status_code, 'Error returned from'
                    ' json module while processing %(url)s: %(err)s\n%(output)s' %
                    {
                        'url': to_bytes(method),
                        'err': to_bytes(e),
                        'output': to_bytes(output.text),
                    })

            # Successfully returned data
            break

        data = munchify(data)

        return data

    def login(self, username, password, otp=None):
        """ Open a session for the user.

        Log in the user with the specified username and password
        against the FAS OpenID server.

        :arg username: the FAS username of the user that wants to log in
        :arg password: the FAS password of the user that wants to log in
        :kwarg otp: currently unused.  Eventually a way to send an otp to the
            API that the API can use.

        """
        response = openid_login(
            session=self._session,
            login_url=self.login_url,
            username=username,
            password=password,
            otp=otp,
            openid_insecure=self.openid_insecure)
        self._save_cookies()
        return response

    @property
    def session_key(self):
        return "%s:%s" % (self.base_url, self.username or '')

    def has_cookies(self):
        return bool(self._session.cookies)

    def _load_cookies(self):
        if not self.cache_session:
            return

        try:
            with self.cache_lock:
                with open(b_SESSION_FILE, 'rb') as f:
                    data = json.loads(f.read())
            for key, value in data[self.session_key]:
                self._session.cookies[key] = value
        except KeyError:
            log.debug("No pre-existing session for %s" % self.session_key)
        except IOError:
            # The file doesn't exist, so create it.
            log.debug("Creating %s", b_SESSION_FILE)
            with open(b_SESSION_FILE, 'wb') as f:
                f.write(json.dumps({}))

    def _save_cookies(self):
        if not self.cache_session:
            return

        with self.cache_lock:
            try:
                with open(b_SESSION_FILE, 'rb') as f:
                    data = json.loads(f.read())
            except Exception:
                log.warn("Failed to open cookie cache before saving.")
                data = {}

            data[self.session_key] = self._session.cookies.items()
            with open(b_SESSION_FILE, 'wb') as f:
                f.write(json.dumps(data))


__all__ = ('OpenIdBaseClient', 'requires_login')
