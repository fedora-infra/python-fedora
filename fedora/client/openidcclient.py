# -*- coding: utf-8 -*-
#
# Copyright (C) 2016, 2017 Red Hat, Inc.
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

"""Base client for applications relying on OpenID Connect for authentication.

Implementation note: this implementation hardcodes certain endpoints at the IdP
to the ones as implemented by Ipsilon 2.0 and higher.

.. moduleauthor:: Patrick Uiterwijk <puiterwijk@redhat.com>

.. versionadded: 0.3.35

"""

import json
import logging
from threading import Lock
import time
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import socket
import os
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
from uuid import uuid4 as uuidgen
import webbrowser
from wsgiref import simple_server

import requests

from fedora import __version__

PROD_IDP = 'https://id.fedoraproject.org/openidc/'
STG_IDP = 'https://id.stg.fedoraproject.org/openidc/'
DEV_IDP = 'https://iddev.fedorainfracloud.org/openidc/'
# The ports that we will try to use for our webserver
WEB_PORTS = [12345, 23456]


class OpenIDCBaseClient(object):
    # Internal implementation of tokens:
    #  Every app id has its own token cache
    #  The token cache is a json serialized dict
    #  This dict contains uuid: token pairs
    #  Every "token" object is a json dict with the following keys:
    #   idp: The URL of the idp that issued the token
    #   sub: The subject that owns the token
    #   access_token: Token value
    #   token_type: Token type. Currently supported: "Bearer"
    #   expires_at: Token expiration UTC time. NOTE: Even if the expires_at
    #    indicates the token should still be valid, it may have been revoked by
    #    the user! Also, even if it has expired, we might still be able to
    #    refresh the token.
    #   refresh_token: The token we can use to refresh the access token
    #   scopes: A list of scopes that we had requested with the token
    def __init__(self, base_url, app_identifier, use_post=False,
                 id_provider=None, client_id=None, client_secret=None,
                 useragent=None, cachedir=None):
        """Client for interacting with web services relying on OpenID Connect.

        :arg base_url: Base of every URL used to contact the server
        :arg app_identifier: Identifier for storage of retrieved tokens
        :kwarg use_post: Whether to use POST submission of client secrets
            rather than Authorization header
        :kwarg id_provider: URL of the identity provider to get tokens from
        :kwarg client_id: The Client Identifier used to request credentials
        :kwarg client_secret: The client "secret" that goes with the client_id.
            Note that since CLI applications are unable to retain secrets, this
            will default to the well-known secret "notsecret".
        :kwarg useragent: Useragent string to use. If not provided, defaults to
            "Fedora OpenIDCBaseClient/VERSION"
        :kwarg cachedir: The directory in which to store the token caches. Will
            be put through expanduer. Default is ~/.fedora. If this does not
            exist and we are unable to create it, the OSError will e thrown up.
        """
        self.logger = logging.getLogger(__name__)
        self.debug = self.logger.debug

        self.base_url = base_url
        self.app_id = app_identifier
        self.use_post = use_post
        self.idp = id_provider or PROD_IDP
        self.client_id = client_id or 'python-fedora'
        self.client_secret = client_secret or 'notsecret'
        self.useragent = useragent or 'Fedora OpenIDCClient/%s' % __version__
        self.cachedir = os.path.expanduser(cachedir or '~/.fedora')
        self.last_returned_uuid = None
        self.problem_reported = False
        self.token_to_try = None
        self._retrieved_code = None
        # TODO: Make cache_lock a filesystem lock so we also lock across
        # multiple invocations
        self._cache_lock = Lock()
        with self._cache_lock:
            self.__refresh_cache()
        self._valid_cache = []

    def get_token(self, scopes, new_token=True):
        """Function to retrieve tokens with specific scopes.

        This function will block until a token is retrieved if requested.
        It is always safe to call this though, since if we already have a token
        with the current app_identifier that has the required scopes, we weill
        return it.

        This function will return a bearer token or None.
        Note that the bearer token might have been revoked by the user or
        expired.
        In that case, you will want to call report_token_issue() to try to
        renew the token or delete the token.

        :kwarg scopes: A list of scopes required for the current client.
        :kwarg new_token: If True, we will actively request the user to get a
            new token with the current scopeset if we do not already have on.
        """
        if not isinstance(scopes, list):
            raise Exception('Scopes must be a list')
        token = self._get_token_with_scopes(scopes)
        if token:
            # If we had a valid token, use that
            self.last_returned_uuid = token[0]
            self.problem_reported = False
            return token[1]['access_token']
        elif not new_token:
            return None

        # We did not have a valid token, now comes the hard part...
        uuid = self._get_new_token(scopes)
        if uuid:
            self.last_returned_uuid = uuid
            self.problem_reported = False
            return self._cache[uuid]['access_token']

    def report_token_issue(self):
        """Report an error with the last token that was returned.

        This will attempt to renew the token that was last returned.
        If that worked, we will return the new access token.
        If it did not work, we will return None and remove this token from the
        cache.

        If you get an indication from your application that the token you sent
        was invalid, you should call it.
        You should explicitly NOT call this function if the token was valid but
        your request failed due to a server error or because the account or
        token was lacking specific permissions.
        """
        if not self.last_returned_uuid:
            raise Exception('Cannot report issue before requesting token')
        if self.problem_reported:
            # We were reported an issue before. Let's just remove this token.
            self._delete_token(self.last_returned_uuid)
            return None
        refresh_result = self._refresh_token(self.last_returned_uuid)
        if not refresh_result:
            self._delete_token(self.last_returned_uuid)
            return None
        else:
            self.problem_reported = True
            return self._cache[self.last_returned_uuid]['access_token']

    def send_request(self, method, scopes, verb='POST', new_token=True,
                     **kwargs):
        """Make an HTTP request to a server method.

        The given method is called with any parameters set in kwargs. If auth
        is True, then the request is made with an authenticated token.

        :arg method: Method to call on the server. It's a URL fragment that is
            appended to the :attr:`base_url` set in :meth:`__init__`.
        :kwarg scopes: Scopes required for this call. If a token is not present
            with this token, a new one will be requested unless nonblocking is
            True.
        :kwarg verb: The HTTP verb to use for this request.
        :kwarg new_token: If True, we will actively request the user to get a
            new token with the current scopeset if we do not already have on.
        :kwarg kwargs: Extra parameters to send to the server.
        """
        is_retry = False
        if self.token_to_try:
            is_retry = True
            token = self.token_to_try
            self.token_to_try = None
        else:
            token = self.get_token(scopes, new_token=new_token)
            if not token:
                return None

        headers = {}
        data = kwargs

        if self.use_post:
            data['access_token'] = token
        else:
            headers['Authorization'] = 'Bearer %s' % token
        resp = requests.request(verb,
                                self.base_url + method,
                                headers=headers,
                                data=data)
        if resp.status_code == 401 and not is_retry:
            self.token_to_try = self.report_token_issue()
            if not self.token_to_try:
                return resp
            return self.send_request(method=method,
                                     scopes=scopes,
                                     verb=verb,
                                     new_token=new_token,
                                     **kwargs)
        elif resp.status_code == 401:
            # We got a 401 and this is a retry. Report error
            self.report_token_issue()
        else:
            return resp

    @property
    def _cachefile(self):
        assert self._cache_lock.locked()
        return os.path.join(self.cachedir, 'oidc_%s.json' % self.app_id)

    def __refresh_cache(self):
        assert self._cache_lock.locked()
        self.debug('Refreshing cache')
        if not os.path.isdir(self.cachedir):
            self.debug('Creating directory')
            os.makedirs(self.cachedir)
        if not os.path.exists(self._cachefile):
            self.debug('Creating file')
            with open(self._cachefile, 'w') as f:
                f.write(json.dumps({}))
        with open(self._cachefile, 'r') as f:
            self._cache = json.loads(f.read())
        self.debug('Loaded %i tokens', len(self._cache))

    def _refresh_cache(self):
        with self._cache_lock:
            self.__refresh_cache()

    def __write_cache(self):
        assert self._cache_lock.locked()
        self.debug('Writing cache with %i tokens', len(self._cache))
        with open(self._cachefile, 'w') as f:
            f.write(json.dumps(self._cache))

    def _add_token(self, token):
        uuid = uuidgen().get_hex()
        self.debug('Adding token %s to cache', uuid)
        with self._cache_lock:
            self.__refresh_cache()
            self._cache[uuid] = token
            self.__write_cache()
        return uuid

    def _delete_token(self, uuid):
        self.debug('Removing token %s from cache', uuid)
        with self._cache_lock:
            self.__refresh_cache()
            if uuid in self._cache:
                self.debug('Removing token')
                del self._cache[uuid]
                self.__write_cache()
            else:
                self.debug('Token was already gone')

    def _get_token_with_scopes(self, scopes):
        possible_token = None
        self.debug('Trying to get token with scopes %s', scopes)
        for uuid in self._cache:
            self.debug('Checking %s', uuid)
            token = self._cache[uuid]
            if token['idp'] != self.idp:
                self.debug('Incorrect idp')
                continue
            if not set(scopes).issubset(set(token['scopes'])):
                self.debug('Missing scope: %s not subset of %s',
                           set(scopes),
                           set(token['scopes']))
                continue
            if token['expires_at'] < time.time():
                # This is a token that's supposed to still be valid, prefer it
                # over any others we have
                self.debug('Not yet expired, returning')
                return uuid, token
            # This is a token that may or may not still be valid
            self.debug('Possible')
            possible_token = (uuid, token)
        if possible_token:
            self.debug('Returning possible token')
            return possible_token

    def _idp_url(self, endpoint):
        return self.idp + endpoint

    def _refresh_token(self, uuid):
        oldtoken = self._cache[uuid]
        self.debug('Refreshing token %s', uuid)
        resp = requests.request(
            'POST',
            self._idp_url('Token'),
            data={'client_id': self.client_id,
                  'client_secret': self.client_secret,
                  'grant_type': 'refresh_token',
                  'refresh_token': oldtoken['refresh_token']})
        resp.raise_for_status()
        resp = resp.json()
        if 'error' in resp:
            self.debug('Unable to refresh, error: %s', resp['error'])
            return False
        self._cache[uuid]['access_token'] = resp['access_token']
        self._cache[uuid]['token_type'] = resp['token_type']
        self._cache[uuid]['refresh_token'] = resp['refresh_token']
        self._cache[uuid]['expires_at'] = time.time() + resp['expires_in']
        self.debug('Refreshed until %s', self._cache[uuid]['expires_at'])
        return True

    def _get_server(self, app):
        """This function returns a SimpleServer with an available WEB_PORT."""
        for port in WEB_PORTS:
            try:
                server = simple_server.make_server('0.0.0.0', port, app)
                return server
            except socket.error:
                # This port did not work. Switch to next one
                continue

    def _get_new_token(self, scopes):
        """This function kicks off some magic.

        We will start a new webserver on one of the WEB_PORTS, and then either
        show the user a URL, or if possible, kick off their browser.
        This URL will be the Authorization endpoint of the IdP with a request
        for our client_id to get a new token with the specified scopes.
        The webserver will then need to catch the return with either an
        Authorization Code (that we will exchange for an access token) or the
        cancellation message.

        This function will store the new token in the local cache, add it to
        the valid cache, and then return the UUID.
        If the user cancelled (or we got another error), we will return None.
        """
        def _token_app(environ, start_response):
            query = environ['QUERY_STRING']
            split = query.split('&')
            kv = dict([v.split('=', 1) for v in split])

            if 'error' in kv:
                self.debug('Error code returned: %s (%s)',
                           kv['error'], kv.get('error_description'))
                self._retrieved_code = False
            else:
                self._retrieved_code = kv['code']

            # Just return a message
            out = StringIO()
            out.write('You can close this window and return to the CLI')
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [out.getvalue()]

        self._retrieved_code = None
        server = self._get_server(_token_app)
        if not server:
            raise Exception('We were unable to instantiate a webserver')
        return_uri = 'http://localhost:%i/' % server.socket.getsockname()[1]
        rquery = {}
        rquery['scope'] = ' '.join(scopes)
        rquery['response_type'] = 'code'
        rquery['client_id'] = self.client_id
        rquery['redirect_uri'] = return_uri
        rquery['response_mode'] = 'query'
        query = urlencode(rquery)
        authz_url = '%s?%s' % (self._idp_url('Authorization'), query)
        print('Please visit %s to grant authorization' % authz_url)
        webbrowser.open(authz_url)
        server.handle_request()
        server.server_close()

        assert self._retrieved_code is not None
        if self._retrieved_code is False:
            # The user cancelled the request
            self._retrieved_code = None
            self.debug('User cancelled')
            return None

        self.debug('We got an authorization code!')
        resp = requests.request(
            'POST',
            self._idp_url('Token'),
            data={'client_id': self.client_id,
                  'client_secret': self.client_secret,
                  'grant_type': 'authorization_code',
                  'redirect_uri': return_uri,
                  'code': self._retrieved_code})
        resp.raise_for_status()
        self._retrieved_code = None
        resp = resp.json()
        if 'error' in resp:
            self.debug('Error exchanging authorization code: %s',
                       resp['error'])
            return None
        token = {'access_token': resp['access_token'],
                 'refresh_token': resp['refresh_token'],
                 'expires_at': time.time() + int(resp['expires_in']),
                 'idp': self.idp,
                 'token_type': resp['token_type'],
                 'scopes': scopes}
        # AND WE ARE DONE! \o/
        return self._add_token(token)
