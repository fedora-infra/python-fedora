#
# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009  Red Hat, Inc.
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
"""
Cross-site Request Forgery Protection.

http://en.wikipedia.org/wiki/Cross-site_request_forgery


.. moduleauthor:: John (J5) Palmieri <johnp@redhat.com>
.. moduleauthor:: Luke Macken <lmacken@redhat.com>
"""

import logging

from webob import Request
from paste.httpexceptions import HTTPFound
from paste.response import replace_header
from urlparse import urlparse, urlunparse
from urllib import urlencode
from repoze.who.interfaces import IMetadataProvider
from zope.interface import implements

try:
    from urlparse import parse_qs
except:
    from cgi import parse_qs

try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

log = logging.getLogger(__name__)

def update_qs(uri, d):
    """
    Helper function for updating query string values.  Similar to calling
    update on a dictionary except we modify the query string of the uri
    instead of another dictionary.
    """
    loc = list(urlparse(uri))
    query_dict = parse_qs(loc[4])
    query_dict.update(d)

    # seems that we have to sanitize a bit here
    query_list = []
    for k, v in query_dict.items():
        if isinstance(v, list):
            for item in v:
                query_list.append((k, item))
        else:
            query_list.append((k, v))

    loc[4] = urlencode(query_list)

    return urlunparse(loc)


class CSRFProtectionMiddleware(object):
    """
    CSRF Protection WSGI Middleware.

    A layer of WSGI middleware that is responsible for making sure authenticated
    requests originated from the user inside of the app's domain
    and not a malicious website.

    This middleware works with the :mod:`repoze.who` middleware, and requires
    that it is placed below :mod:`repoze.who` in the WSGI stack,
    since it relies upon ``repoze.who.identity`` to exist in the environ before
    it is called.

    This middleware is enabled by default when using Moksha, and can be
    disabled by setting ``moksha.csrf_protection = False`` in your
    configuration file.

    To utilize this middleware without Moksha, you can just add it to your
    WSGI below the :mod:`repoze.who` middleware.  Here is an example of
    utilizing the `CSRFProtectionMiddleware` within a TurboGears2 application.
    In your ``project/config/middleware.py``, you would wrap your main
    application with the `CSRFProtectionMiddleware`, like so:

    .. code-block:: python

        def make_app(global_conf, full_stack=True, **app_conf):
            from moksha.middleware.csrf import CSRFProtectionMiddleware
            app = make_base_app(global_conf, wrap_app=CSRFProtectionMiddleware,
                                full_stack=full_stack, **app_conf)

    The :class:`moksha.api.widgets.moksha:MokshaGlobals` widget then needs to
    be rendered in every page, which automatically handles injecting the CSRF
    token.  This widget is registerd as a Moksha Global Resource, and Moksha's
    default index template handles injecting this by default, but you
    can easily render Moksha's global resource injection widget in your own
    applications template by doing the following in your master template::

        ${tmpl_context.moksha_global_resources()}

    URLs can then be re-written using the ``moksha.csrf_rewrite_url`` function
    that is in the ``moksha.js`` library, which is automatically pulled in by
    the MokshaGlobals widget.  Here is an example of adding the CSRF token to
    an ajax.  This example also utilizes the ``moksha.filter_resources``
    function to strip out any duplicate javascript files.

    .. code-block:: javascript

        $.ajax({
            url: moksha.csrf_rewrite_url('/widgets/%(id)s'),
            success: function(data, status) {
                var $panel = $('#%(id)s_panel');
                var $stripped = moksha.filter_resources(data);
                $panel.html($stripped);
            }
        });
    """

    def __init__(self, application, csrf_token_id='_csrf_token',
                 clear_env='repoze.who.identity repoze.what.credentials',
                 token_env='CSRF_TOKEN', auth_state='CSRF_AUTH_STATE'):
        """
        Initialize the CSRF Protection WSGI Middleware.

        :csrf_token_id: The name of the CSRF token variable
        :clear_env: Variables to clear out of the `environ` on invalid token
        :token_env: The name of the token variable in the environ
        :auth_state: The environ key that will be set when we are logging in
        """
        log.info('Creating CSRFProtectionMiddleware')
        self.application = application
        self.csrf_token_id = csrf_token_id
        self.clear_env = clear_env
        self.token_env = token_env
        self.auth_state = auth_state

    def __call__(self, environ, start_response):
        """
        This method is called for each request.  It looks for a user-supplied
        CSRF token in the GET/POST parameters, and compares it to the token
        attached to ``environ['repoze.who.identity']['_csrf_token']``.  If it
        does not match, or if a token is not provided, it will remove the
        user from the ``environ``, based on the ``clear_env`` setting.
        """
        request = Request(environ)
        log.debug("CSRFProtectionMiddleware(%s)" % request.path)

        token = environ.get('repoze.who.identity', {}).get(self.csrf_token_id)
        csrf_token = environ.get(self.token_env)

        if token and csrf_token and token == csrf_token:
            log.debug("User supplied CSRF token matches environ!")
        else:
            if not environ.get(self.auth_state):
                log.debug("Clearing identity")
                CSRFMetadataProvider.clean_environ(environ, self.clear_env)
                if csrf_token:
                    log.warning("Invalid CSRF token.  User supplied (%s) "
                                "does not match what's in our environ (%s)"
                                % (csrf_token, token))
                    if not environ.get(self.auth_state):
                        log.debug("Logging the user out")
                        request.path_info = '/logout_handler'
                        response = request.get_response(self.application)
                        response.status = '401'
                        return response(environ, start_response)

        response = request.get_response(self.application)

        if environ.get(self.auth_state):
            log.debug("CSRF_AUTH_STATE; rewriting headers")
            token = environ.get('repoze.who.identity', {}).get(self.csrf_token_id)

            loc = update_qs(response.location, {self.csrf_token_id: str(token)})
            response.location = loc
            log.debug("response.location = %s" % response.location)
            environ[self.auth_state] = None

        return response(environ, start_response)


class CSRFMetadataProvider(object):
    """
    Repoze.who CSRF Metadata Provider Plugin.

    This metadata provider is called with an authenticated users identity
    automatically by repoze.who.  It will then take the SHA1 hash of the
    users session cookie, and set it as the CSRF token in
    ``environ['repoze.who.identity']['_csrf_token']``.

    This plugin will also set ``CSRF_AUTH_STATE`` in the environ if the user
    has just authenticated during this request.

    This plugin is enabled by default when using Moksha's application stack.
    To enable this plugin in an existing TurboGears2 application, you can
    add the following to your ``project/config/app_cfg.py``

    .. code-block:: python

        from moksha.middleware.csrf import CSRFMetadataProvider
        base_config.sa_auth.mdproviders = [('csrfmd', CSRFMetadataProvider())]

    """
    implements(IMetadataProvider)

    def __init__(self, csrf_token_id='_csrf_token', session_cookie='authtkt',
                 clear_env='repoze.who.identity repoze.what.credentials',
                 login_handler='/post_login', token_env='CSRF_TOKEN',
                 auth_session_id='CSRF_AUTH_SESSION_ID',
                 auth_state='CSRF_AUTH_STATE'):
        """
        Create the CSRF Metadata Provider Plugin.

        :csrf_token_id: The name of the CSRF token variable
        :session_cookie: The name of the session cookie
        :login_handler: The path to the login handler, used to determine if
                        the user logged in during this request
        :token_env: The name of the token variable in the environ
        :auth_session_id: The environ key containing an optional session id
        :auth_state: The environ key that indicates when we are logging in
        """
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
        log.debug("CSRFMetadataProvider.add_metadata(%s)" % request.path)

        session_id = environ.get(self.auth_session_id)
        if not session_id:
            session_id = request.cookies.get(self.session_cookie)
        log.debug('session_id = %r' % session_id)

        if session_id and session_id != 'Set-Cookie:':
            token = sha1(session_id).hexdigest()
            identity.update({self.csrf_token_id: token})
            log.debug("Identity updated with CSRF token")
            path = self.strip_script(environ, request.path)
            if path == self.login_handler:
                log.debug('Setting CSRF_AUTH_STATE')
                environ[self.auth_state] = True
                environ[self.token_env] = token
            else:
                environ[self.token_env] = self.extract_csrf_token(request)

            app = environ.get('repoze.who.application')
            if app:
                # This occurs during login in some application configurations
                if isinstance(app, HTTPFound) and environ.get(self.auth_state):
                    log.debug('Got HTTPFound(302) from repoze.who.application')
                    loc = update_qs(app.location(), {self.csrf_token_id: str(token)})

                    replace_header(app.headers, 'location', loc)
                    log.debug('Altered headers: %s' % str(app.headers))
        else:
            log.warning("Invalid session cookie %r, not setting CSRF token!" %session_id)

    def extract_csrf_token(self, request):
        """ Extract and remove the CSRF token from a given :class:`webob.Request` """
        csrf_token = None

        if self.csrf_token_id in request.GET:
            log.debug("%s in GET" % self.csrf_token_id)
            csrf_token = request.GET[self.csrf_token_id]
            del(request.GET[self.csrf_token_id])
            request.query_string = '&'.join(['%s=%s' % (k, v) for k, v in
                                             request.GET.items()])

        if self.csrf_token_id in request.POST:
            log.debug("%s in POST" % self.csrf_token_id)
            csrf_token = request.POST[self.csrf_token_id]
            del(request.POST[self.csrf_token_id])

        return csrf_token

    @classmethod
    def clean_environ(cls, environ, keys):
        """ Delete the ``keys`` from the supplied ``environ`` """
        log.debug('clean_environ(%s)' % keys)
        for key in keys.split():
            if key in environ:
                log.debug("Deleting %s from environ" % key)
                del(environ[key])
