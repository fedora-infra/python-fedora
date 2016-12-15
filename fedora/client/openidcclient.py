#!/usr/bin/env python2 -tt
# -*- coding: utf-8 -*-
#
# Copyright (C) 2016  Red Hat, Inc.
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
import requests
from StringIO import StringIO
import socket
import os
import urllib
from uuid import uuid4 as uuidgen
import webbrowser
from wsgiref import simple_server

from fedora import __version__

PROD_IDP = 'https://id.fedoraproject.org/openidc/'
STG_IDP = 'https://id.stg.fedoraproject.org/openidc/'
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
                 useragent=None, cachedir=None, socket_addr='127.0.0.1'):
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
        self.socket_addr = socket_addr
        # TODO: Make cache_lock a filesystem lock so we also lock across
        # multiple invocations
        self._cache_lock = Lock()
        with self._cache_lock:
            self.__refresh_cache()
        self._valid_cache = []

    @property
    def cachefile(self):
        assert self._cache_lock.locked()
        return os.path.join(self.cachedir, 'oidc_%s.json' % self.app_id)

    def __refresh_cache(self):
        assert self._cache_lock.locked()
        self.debug('Refreshing cache')
        if not os.path.isdir(self.cachedir):
            self.debug('Creating directory')
            os.makedirs(self.cachedir)
        if not os.path.exists(self.cachefile):
            self.debug('Creating file')
            with open(self.cachefile, 'w') as f:
                f.write(json.dumps({}))
        with open(self.cachefile, 'r') as f:
            self._cache = json.loads(f.read())
        self.debug('Loaded %i tokens' % len(self._cache))

    def _refresh_cache(self):
        with self._cache_lock:
            self.__refresh_cache()

    def __write_cache(self):
        assert self._cache_lock.locked()
        self.debug('Writing cache with %i tokens' % len(self._cache))
        with open(self.cachefile, 'w') as f:
            f.write(json.dumps(self._cache))

    def _add_token(self, token):
        uuid = uuidgen().get_hex()
        self.debug('Adding token %s to cache' % uuid)
        with self._cache_lock:
            self.__refresh_cache()
            self._cache[uuid] = token
            self.__write_cache()
        return uuid

    def _delete_token(self, uuid):
        self.debug('Removing token %s from cache' % uuid)
        with self._cache_lock:
            self._refresh_cache()
            if uuid in self._cache:
                del self._cache[uuid]
                self._write_cache()

    def _get_token_with_scopes(self, scopes):
        possible_token = None
        self.debug('Trying to get token with scopes %s' % scopes)
        for uuid in self._cache:
            self.debug('Checking %s' % uuid)
            token = self._cache[uuid]
            if token['idp'] != self.idp:
                self.debug('Incorrect idp')
                continue
            for scope in scopes:
                if not scope in token['scopes']:
                    self.debug('Missing scope %s' % scope)
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

    def _get_token_info(self, token):
        self.debug('Retrieving token info')
        resp = requests.post(self._idp_url('TokenInfo'),
                             data={'client_id': self.client_id,
                                   'client_secret': self.client_secret,
                                   'token': token['access_token']})
        # TODO: Be a bit more stable in handling if we get a non-JSON object
        return resp.json()

    def _refresh_token(self, uuid):
        oldtoken = self._cache[uuid]
        self.debug('Refreshing token %s' % uuid)
        resp = requests.post(
            self._idp_url('Token'),
            data={'client_id': self.client_id,
                  'client_secret': self.client_secret,
                  'grant_type': 'refresh_token',
                  'refresh_token': oldtoken['refresh_token']})
        # TODO: Be more resilient against different replies
        resp = resp.json()
        if 'error' in resp:
            self.debug('Unable to refresh, error: %s' % resp['error'])
            return False
        self._cache[uuid]['access_token'] = resp['access_token']
        self._cache[uuid]['token_type'] = resp['token_type']
        self._cache[uuid]['refresh_token'] = resp['refresh_token']
        self._cache[uuid]['expires_at'] = time.time() + resp['expires_in']
        self.debug('Refreshed until %s' % self._cache[uuid]['expires_at'])
        return True

    def _get_valid_token_with_scopes(self, scopes):
        while True:
            token = self._get_token_with_scopes(scopes)
            if not token:
                break
            uuid, token = token
            if uuid in self._valid_cache:
                return token
            tokeninfo = self._get_token_info(token)
            if not tokeninfo['active']:
                if self._refresh_token(uuid):
                    token = self._cache[uuid]
                else:
                    # This token was invalid and could not be refreshed
                    self._delete_token(uuid)
                    continue
            # We either refreshed it, 
            self._valid_cache.append(uuid)
            return token

    def _get_server(self, app):
        """This function returns a SimpleServer with an available WEB_PORT."""
        for port in WEB_PORTS:
            try:
                server = simple_server.make_server(self.socket_addr, port, app)
                return server
            except socket.error:
                # This port did not work. Switch to next one
                continue
        # Re-raise the last socket.error if we couldn't find a port.
        raise

    def _get_new_token(self, scopes):
        """This function kicks off some magic.

        We will start a new webserver on one of the WEB_PORTS, and then either
        show the user a URL, of if possible, kick off their browser.
        This URL will be the Authorization endpoint of the IdP with a request
        for our client_id to get a new token with the specified scopes.
        The webserver will then need to catch the return with either an
        Authorization Code (that we will exchange for an access token) or the
        cancellation message.

        This function will store the new token in the local cache, add it to
        the valid cache, and then return the UUID.
        If the user cancelled (or we got another error), we will return None.
        """
        def token_app(environ, start_response):
            query = environ['QUERY_STRING']
            split = query.split('&')
            kv = dict([v.split('=', 1) for v in split])

            if 'error' in kv:
                self.debug('Error code returned: %s (%s)'
                           % (kv['error'], kv.get('error_description')))
                self.__retrieved_code = False
            else:
                self.__retrieved_code = kv['code']

            # Just return a message
            out = StringIO()
            print >>out, "You can close this window and return to the CLI"
            start_response('200 OK', [('Content-Type', 'text/plain')])
            return [out.getvalue()]

        self.__retrieved_code = None
        server = self._get_server(token_app)
        if not server:
            raise Exception('We were unable to instantiate a webserver')
        return_uri = 'http://localhost:%i/' % server.socket.getsockname()[1]
        query = {}
        # We always silently inject scope openid so we get an id_token
        if len(scopes) > 0:
            query['scope'] = 'openid %s' % ' '.join(scopes)
        else:
            query['scope'] = 'openid'
        query['response_type'] = 'code'
        query['client_id'] = self.client_id
        query['redirect_uri'] = return_uri
        query['state'] = 'ignored'
        query['response_mode'] = 'query'
        query = urllib.urlencode(query)
        authz_url = '%s?%s' % (self._idp_url('Authorization'), query)
        print('Please visit %s to grant authorization' % authz_url)
        webbrowser.open(authz_url)
        server.handle_request()
        server.server_close()

        assert self.__retrieved_code is not None
        if self.__retrieved_code is False:
            # The user cancelled the request
            self.__retrieved_code = None
            self.debug('User cancelled')
            return None

        self.debug('We got an authorization code!')
        resp = requests.post(
            self._idp_url('Token'),
            data={'client_id': self.client_id,
                  'client_secret': self.client_secret,
                  'grant_type': 'authorization_code',
                  'redirect_uri': return_uri,
                  'code': self.__retrieved_code})
        self.__retrieved_code = None
        # TODO: Handle other responses
        resp = resp.json()
        if 'error' in resp:
            self.debug('Error exchanging authorization code: %s'
                       % resp['error'])
            return None
        token = {'access_token': resp['access_token'],
                 'refresh_token': resp['refresh_token'],
                 'expires_at': time.time() + int(resp['expires_in']),
                 'idp': self.idp,
                 'token_type': resp['token_type'],
                 'scopes': scopes}
        # AND WE ARE DONE! \o/
        return self._add_token(token)

    def get_token(self, scopes, new_token=True):
        """Function to retrieve tokens with specific scopes.
        
        This function will block until a token is retrieved.
        It is always safe to call this though, since if we already have a token
        with the current app_identifier that has the required scopes that is
        still valid.
        This function will also use any available refresh tokens to refresh if
        the token has expired.

        This function will return a valid bearer token or throw an exception.

        :kwarg scopes: A list of scopes required for the current client.
        :kwarg new_token: If True, we will actively request the user to get a
            new token with the current scopeset if we do not already have on.
        """
        token = self._get_valid_token_with_scopes(scopes)
        if token:
            # If we had a valid token, use that
            return token['access_token']

        # We did not have a valid token, now comes the hard part...
        uuid = self._get_new_token(scopes)
        if uuid:
            return self._cache[uuid]['access_token']

    def send_request(self, method, scopes=None, verb='POST', new_token=True,
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
        token = self.get_token(scopes, new_token=new_token)
        if not token:
            return None

        headers = {}
        data = kwargs

        if self.use_post:
            data['access_token'] = token['access_token']
        else:
            headers['Authorization'] = 'Bearer %s' % token['access_token']
        return requests.request(verb,
                                self.base_url + method,
                                headers=headers,
                                data=data)
