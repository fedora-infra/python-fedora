#
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2011  Red Hat, Inc.
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
'''
Cross-site Request Forgery Protection.

http://en.wikipedia.org/wiki/Cross-site_request_forgery


.. moduleauthor:: John (J5) Palmieri <johnp@redhat.com>
.. moduleauthor:: Luke Macken <lmacken@redhat.com>

.. versionadded:: 0.3.17
'''

import logging

from bunch import Bunch
from kitchen.text.converters import to_bytes
from webob import Request
try:
    # webob > 1.0
    from webob.headers import ResponseHeaders
except ImportError:
    # webob < 1.0
    from webob.headerdict import HeaderDict as ResponseHeaders
from paste.httpexceptions import HTTPFound
from paste.response import replace_header
from repoze.who.interfaces import IMetadataProvider
from zope.interface import implements

try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

from fedora.urlutils import update_qs
from fedora import b_

log = logging.getLogger(__name__)


class CSRFProtectionMiddleware(object):
    '''
    CSRF Protection WSGI Middleware.

    A layer of WSGI middleware that is responsible for making sure authenticated
    requests originated from the user inside of the app's domain
    and not a malicious website.

    This middleware works with the :mod:`repoze.who` middleware, and requires
    that it is placed below :mod:`repoze.who` in the WSGI stack,
    since it relies upon ``repoze.who.identity`` to exist in the environ before
    it is called.

    To utilize this middleware, you can just add it to your WSGI stack below
    the :mod:`repoze.who` middleware.  Here is an example of utilizing the
    `CSRFProtectionMiddleware` within a TurboGears2 application.
    In your ``project/config/middleware.py``, you would wrap your main
    application with the `CSRFProtectionMiddleware`, like so:

    .. code-block:: python

        from fedora.wsgi.csrf import CSRFProtectionMiddleware
        def make_app(global_conf, full_stack=True, **app_conf):
            app = make_base_app(global_conf, wrap_app=CSRFProtectionMiddleware,
                                full_stack=full_stack, **app_conf)

    You then need to add the CSRF token to every url that you need to be
    authenticated for.  When used with TurboGears2, an overridden version of
    :func:`tg.url` is provided.  You can use it directly by calling::

        from fedora.tg2.utils import url
        [...]
        url = url('/authentication_needed')

    An easier and more portable way to use that is from within TG2 to set this
    up is to use :func:`fedora.tg2.utils.enable_csrf` when you setup your
    application.  This function will monkeypatch TurboGears2's :func:`tg.url`
    so that it adds a csrf token to urls.  This way, you can keep the same
    code in your templates and controller methods whether or not you configure
    the CSRF middleware to provide you with protection via
    :func:`~fedora.tg2.utils.enable_csrf`.
    '''

    def __init__(self, application, csrf_token_id='_csrf_token',
                 clear_env='repoze.who.identity repoze.what.credentials',
                 token_env='CSRF_TOKEN', auth_state='CSRF_AUTH_STATE'):
        '''
        Initialize the CSRF Protection WSGI Middleware.

        :csrf_token_id: The name of the CSRF token variable
        :clear_env: Variables to clear out of the `environ` on invalid token
        :token_env: The name of the token variable in the environ
        :auth_state: The environ key that will be set when we are logging in
        '''
        log.info(b_('Creating CSRFProtectionMiddleware'))
        self.application = application
        self.csrf_token_id = csrf_token_id
        self.clear_env = clear_env.split()
        self.token_env = token_env
        self.auth_state = auth_state

    def _clean_environ(self, environ):
        ''' Delete the ``keys`` from the supplied ``environ`` '''
        log.debug(b_('clean_environ(%s)') % to_bytes(self.clear_env))
        for key in self.clear_env:
            if key in environ:
                log.debug(b_('Deleting %(key)s from environ') %
                    {'key': to_bytes(key)})
                del(environ[key])

    def __call__(self, environ, start_response):
        '''
        This method is called for each request.  It looks for a user-supplied
        CSRF token in the GET/POST parameters, and compares it to the token
        attached to ``environ['repoze.who.identity']['_csrf_token']``.  If it
        does not match, or if a token is not provided, it will remove the
        user from the ``environ``, based on the ``clear_env`` setting.
        '''
        request = Request(environ)
        log.debug(b_('CSRFProtectionMiddleware(%(r_path)s)') %
                {'r_path': to_bytes(request.path)})

        token = environ.get('repoze.who.identity', {}).get(self.csrf_token_id)
        csrf_token = environ.get(self.token_env)

        if token and csrf_token and token == csrf_token:
            log.debug(b_('User supplied CSRF token matches environ!'))
        else:
            if not environ.get(self.auth_state):
                log.debug(b_('Clearing identity'))
                self._clean_environ(environ)
                if 'repoze.who.identity' not in environ:
                    environ['repoze.who.identity'] = Bunch()
                if 'repoze.who.logins' not in environ:
                    # For compatibility with friendlyform
                    environ['repoze.who.logins'] = 0
                if csrf_token:
                    log.warning(b_('Invalid CSRF token.  User supplied'
                            ' (%(u_token)s) does not match what\'s in our'
                            ' environ (%(e_token)s)') %
                            {'u_token': to_bytes(csrf_token),
                            'e_token': to_bytes(token)})

        response = request.get_response(self.application)

        if environ.get(self.auth_state):
            log.debug(b_('CSRF_AUTH_STATE; rewriting headers'))
            token = environ.get('repoze.who.identity', {})\
                    .get(self.csrf_token_id)

            loc = update_qs(response.location, {self.csrf_token_id: str(token)})
            response.location = loc
            log.debug(b_('response.location = %(r_loc)s') %
                    {'r_loc': to_bytes(response.location)})
            environ[self.auth_state] = None

        return response(environ, start_response)


class CSRFMetadataProvider(object):
    '''
    Repoze.who CSRF Metadata Provider Plugin.

    This metadata provider is called with an authenticated users identity
    automatically by repoze.who.  It will then take the SHA1 hash of the
    users session cookie, and set it as the CSRF token in
    ``environ['repoze.who.identity']['_csrf_token']``.

    This plugin will also set ``CSRF_AUTH_STATE`` in the environ if the user
    has just authenticated during this request.

    To enable this plugin in a TurboGears2 application, you can
    add the following to your ``project/config/app_cfg.py``

    .. code-block:: python

        from fedora.wsgi.csrf import CSRFMetadataProvider
        base_config.sa_auth.mdproviders = [('csrfmd', CSRFMetadataProvider())]

    Note: If you use the faswho plugin, this is turned on automatically.
    '''
    implements(IMetadataProvider)

    def __init__(self, csrf_token_id='_csrf_token', session_cookie='tg-visit',
                 clear_env='repoze.who.identity repoze.what.credentials',
                 login_handler='/post_login', token_env='CSRF_TOKEN',
                 auth_session_id='CSRF_AUTH_SESSION_ID',
                 auth_state='CSRF_AUTH_STATE'):
        '''
        Create the CSRF Metadata Provider Plugin.

        :kwarg csrf_token_id: The name of the CSRF token variable. The
            identity will contain an entry with this as key and the
            computed csrf_token as the value.
        :kwarg session_cookie: The name of the session cookie
        :kwarg login_handler: The path to the login handler, used to determine
            if the user logged in during this request
        :kwarg token_env: The name of the token variable in the environ.
            The environ will contain the token from the request
        :kwarg auth_session_id: The environ key containing an optional
            session id
        :kwarg auth_state: The environ key that indicates when we are
            logging in
        '''
        self.csrf_token_id = csrf_token_id
        self.session_cookie = session_cookie
        self.clear_env = clear_env
        self.login_handler = login_handler
        self.token_env = token_env
        self.auth_session_id = auth_session_id
        self.auth_state = auth_state

    def strip_script(self, environ, path):
        # Strips the script portion of a url path so the middleware works even
        # when mounted under a path other than root
        if path.startswith('/') and 'SCRIPT_NAME' in environ:
            prefix = environ.get('SCRIPT_NAME')
            if prefix.endswith('/'):
                prefix = prefix[:-1]

            if path.startswith(prefix):
                path = path[len(prefix):]

        return path

    def add_metadata(self, environ, identity):
        request = Request(environ)
        log.debug(b_('CSRFMetadataProvider.add_metadata(%(r_path)s)')
                % {'r_path': to_bytes(request.path)})

        session_id = environ.get(self.auth_session_id)
        if not session_id:
            session_id = request.cookies.get(self.session_cookie)
        log.debug(b_('session_id = %(s_id)r') % {'s_id':
                to_bytes(session_id)})

        if session_id and session_id != 'Set-Cookie:':
            environ[self.auth_session_id] = session_id
            token = sha1(session_id).hexdigest()
            identity.update({self.csrf_token_id: token})
            log.debug(b_('Identity updated with CSRF token'))
            path = self.strip_script(environ, request.path)
            if path == self.login_handler:
                log.debug(b_('Setting CSRF_AUTH_STATE'))
                environ[self.auth_state] = True
                environ[self.token_env] = token
            else:
                environ[self.token_env] = self.extract_csrf_token(request)

            app = environ.get('repoze.who.application')
            if app:
                # This occurs during login in some application configurations
                if isinstance(app, HTTPFound) and environ.get(self.auth_state):
                    log.debug(b_('Got HTTPFound(302) from'
                        ' repoze.who.application'))
                    # What possessed people to make this a string or
                    # a function?
                    location = app.location
                    if hasattr(location, '__call__'):
                        location = location()
                    loc = update_qs(location, {self.csrf_token_id:
                        str(token)})

                    headers = app.headers.items()
                    replace_header(headers, 'location', loc)
                    app.headers = ResponseHeaders(headers)
                    log.debug(b_('Altered headers: %(headers)s') % {'headers':
                        to_bytes(app.headers)})
        else:
            log.warning(b_('Invalid session cookie %(s_id)r, not setting CSRF'
                ' token!') % {'s_id': to_bytes(session_id)})

    def extract_csrf_token(self, request):
        '''Extract and remove the CSRF token from a given
        :class:`webob.Request`
        '''
        csrf_token = None

        if self.csrf_token_id in request.GET:
            log.debug(b_("%(token)s in GET") % {'token':
                to_bytes(self.csrf_token_id)})
            csrf_token = request.GET[self.csrf_token_id]
            del(request.GET[self.csrf_token_id])
            request.query_string = '&'.join(['%s=%s' % (k, v) for k, v in
                                             request.GET.items()])

        if self.csrf_token_id in request.POST:
            log.debug(b_("%(token)s in POST") % {'token':
                to_bytes(self.csrf_token_id)})
            csrf_token = request.POST[self.csrf_token_id]
            del(request.POST[self.csrf_token_id])

        return csrf_token
