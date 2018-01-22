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
import os

import lockfile
import requests
import requests.adapters
from requests.packages.urllib3.util import Retry
from six.moves.urllib.parse import urljoin

from functools import wraps
from munch import munchify
from kitchen.text.converters import to_bytes

from fedora import __version__
from fedora.client import (AuthError,
                           LoginRequiredError,
                           ServerError,
                           UnsafeFileError,
                           check_file_permissions)
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
        elif output.status_code == 403:
            raise LoginRequiredError(
                '{0} requires a logged in user'.format(output.url))
        return output
    return wraps(func)(_decorator)


class OpenIdBaseClient(OpenIdProxyClient):

    """ A client for interacting with web services relying on openid auth. """

    def __init__(self, base_url, login_url=None, useragent=None, debug=False,
                 insecure=False, openid_insecure=False, username=None,
                 cache_session=True, retries=None, timeout=None,
                 retry_backoff_factor=0):
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
            Note that this can only be set during object initialization.
        :kwarg timeout: A float describing the timeout of the connection. The
            timeout only affects the connection process itself, not the
            downloading of the response body. Defaults to 120 seconds.
        :kwarg retry_backoff_factor: Exponential backoff factor to apply in
            between retry attempts.  We will sleep for:

                `{retry_backoff_factor}*(2 ^ ({number of failed retries} - 1))`

            ...seconds inbetween attempts.  The backoff factor scales the rate
            at which we back off.   Defaults to 0 (backoff disabled).
            Note that this attribute can only be set at object initialization.
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

        # Also hold on to retry logic.
        # http://www.coglib.com/~icordasc/blog/2014/12/retries-in-requests.html
        server_errors = [500, 501, 502, 503, 504, 506, 507, 508, 509, 599]
        method_whitelist = Retry.DEFAULT_METHOD_WHITELIST.union(set(['POST']))
        if retries is not None:
            prefixes = ['http://', 'https://']
            for prefix in prefixes:
                self._session.mount(prefix, requests.adapters.HTTPAdapter(
                    max_retries=Retry(
                        total=retries,
                        status_forcelist=server_errors,
                        backoff_factor=retry_backoff_factor,
                        method_whitelist=method_whitelist,
                    ),
                ))

        # See if we have any cookies kicking around from a previous run
        self._load_cookies()

    def _initialize_session_cache(self):
        # Note -- fallback to returning None on any problems as this isn't
        # critical.  It just makes it so that we don't have to ask the user
        # for their password over and over.
        if not os.path.isdir(b_SESSION_DIR):
            try:
                os.makedirs(b_SESSION_DIR, mode=0o750)
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

    def send_request(self, method, auth=False, verb='POST', **kwargs):
        """Make an HTTP request to a server method.

        The given method is called with any parameters set in req_params.  If
        auth is True, then the request is made with an authenticated session
        cookie.

        :arg method: Method to call on the server.  It's a url fragment that
            comes after the :attr:`base_url` set in :meth:`__init__`.
        :kwarg auth: If True perform auth to the server, else do not.
        :kwarg req_params: Extra parameters to send to the server.
        :kwarg file_params: dict of files where the key is the name of the
            file field used in the remote method and the value is the local
            path of the file to be uploaded.  If you want to pass multiple
            files to a single file field, pass the paths as a list of paths.
        :kwarg verb: HTTP verb to use.  GET and POST are currently supported.
            POST is the default.
        """
        # Decide on the set of auth cookies to use

        method = absolute_url(self.base_url, method)

        self._authed_verb_dispatcher = {(False, 'POST'): self._session.post,
                                        (False, 'GET'): self._session.get,
                                        (True, 'POST'): self._authed_post,
                                        (True, 'GET'): self._authed_get}

        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout

        try:
            func = self._authed_verb_dispatcher[(auth, verb)]
        except KeyError:
            raise Exception('Unknown HTTP verb')

        try:
            output = func(method, **kwargs)
        except LoginRequiredError:
            raise AuthError()

        try:
            data = output.json()
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
        if not username:
            raise AuthError("Username may not be %r at login." % username)
        if not password:
            raise AuthError("Password required for login.")
        # It looks like we're really doing this. Let's make sure that we don't
        # collide various cookies, and clear every cookie we had up until now
        # for this service.
        self._session.cookies.clear()
        self._save_cookies()

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
            check_file_permissions(b_SESSION_FILE, True)
        except UnsafeFileError as e:
            log.debug('Current sessions ignored: {}'.format(str(e)))
            return

        try:
            with self.cache_lock:
                with open(b_SESSION_FILE, 'rb') as f:
                    data = json.loads(f.read(), encoding='utf-8')
            for key, value in data[self.session_key]:
                self._session.cookies[key] = value
        except KeyError:
            log.debug("No pre-existing session for %s" % self.session_key)
        except IOError:
            # The file doesn't exist, so create it.
            log.debug("Creating %s", b_SESSION_FILE)
            oldmask = os.umask(0o027)
            with open(b_SESSION_FILE, 'wb') as f:
                f.write(json.dumps({}).encode('utf-8'))
            os.umask(oldmask)

    def _save_cookies(self):
        if not self.cache_session:
            return

        with self.cache_lock:
            try:
                check_file_permissions(b_SESSION_FILE, True)
                with open(b_SESSION_FILE, 'rb') as f:
                    data = json.loads(f.read(), encoding='utf-8')
            except UnsafeFileError as e:
                log.debug('Clearing sessions: {}'.format(str(e)))
                os.unlink(b_SESSION_FILE)
                data = {}
            except Exception:
                log.warn("Failed to open cookie cache before saving.")
                data = {}

            oldmask = os.umask(0o027)
            data[self.session_key] = self._session.cookies.items()
            with open(b_SESSION_FILE, 'wb') as f:
                f.write(json.dumps(data).encode('utf-8'))
            os.umask(oldmask)


__all__ = ('OpenIdBaseClient', 'requires_login')
