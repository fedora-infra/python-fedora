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
repoze.who plugin to authenticate against hte Fedora Account System

.. moduleauthor:: John (J5) Palmieri <johnp@redhat.com>
.. moduleauthor:: Luke Macken <lmacken@redhat.com>
.. moduleauthor:: Toshio Kuratomi <toshio@fedoraproject.org>

.. versionadded:: 0.3.17
.. versionchanged:: 0.3.26
    - Added secure and httponly as optional attributes to the session cookie
    - Removed too-aggressive caching (wouldn't detect logout from another app)
    - Added ability to authenticate and request a page in one request
'''
import os
import sys
from urllib import quote_plus
import logging

import pkg_resources

from beaker.cache import Cache
from bunch import Bunch
from kitchen.text.converters import to_bytes, exception_to_bytes
from paste.httpexceptions import HTTPFound, HTTPForbidden
from repoze.who.middleware import PluggableAuthenticationMiddleware
from repoze.who.classifiers import default_request_classifier
from repoze.who.classifiers import default_challenge_decider
from repoze.who.interfaces import IChallenger, IIdentifier
from repoze.who.plugins.basicauth import BasicAuthPlugin
from repoze.who.plugins.friendlyform import FriendlyFormPlugin
from paste.request import parse_dict_querystring, parse_formvars
import webob

from fedora import _, b_
from fedora.client import AuthError
from fedora.client.fasproxy import FasProxyClient
from fedora.wsgi.csrf import CSRFMetadataProvider, CSRFProtectionMiddleware

log = logging.getLogger(__name__)

FAS_URL = 'https://admin.fedoraproject.org/accounts/'
FAS_CACHE_TIMEOUT = 900 # 15 minutes (FAS visits timeout after 20)

fas_cache = Cache('fas_repozewho_cache', type='memory')

def fas_request_classifier(environ): 
    classifier = default_request_classifier(environ) 
    if classifier == 'browser': 
        request = webob.Request(environ) 
        if not request.accept.best_match(['application/xhtml+xml','text/html']): 
            classifier = 'app' 
    return classifier 

def make_faswho_middleware(app, log_stream=None, login_handler='/login_handler',
        login_form_url='/login', logout_handler='/logout_handler',
        post_login_url='/post_login', post_logout_url=None, fas_url=FAS_URL,
        insecure=False, ssl_cookie=True, httponly=True):
    '''
    :arg app: WSGI app that is being wrapped
    :kwarg log_stream: :class:`logging.Logger` to log auth messages
    :kwarg login_handler: URL where the login form is submitted
    :kwarg login_form_url: URL where the login form is displayed
    :kwarg logout_handler: URL where the logout form is submitted
    :kwarg post_login_url: URL to redirect the user to after login
    :kwarg post_logout_url: URL to redirect the user to after logout
    :kwarg fas_url: Base URL to the FAS server
    :kwarg insecure: Allow connecting to a fas server without checking the
        server's SSL certificate.  Opens you up to MITM attacks but can be
        useful when testing.  *Do not enable this in production*
    :kwarg ssl_cookie: If :data:`True` (default), tell the browser to only
        send the session cookie back over https.
    :kwarg httponly: If :data:`True` (default), tell the browser that the
        session cookie should only be read for sending to a server, not for
        access by JavaScript or other clientside technology.  This prevents
        using the session cookie to pass information to JavaScript clients but
        also prevents XSS attacks from stealing the session cookie
        information.
    '''

    # Because of the way we override values (via a dict in AppConfig), we
    # need to make this a keyword arg and then check it here to make it act
    # like a positional arg.
    if not log_stream:
        raise TypeError('log_stream must be set when calling make_fasauth_middleware()')

    faswho = FASWhoPlugin(fas_url, insecure=insecure, ssl_cookie=ssl_cookie,
            httponly=httponly)
    csrf_mdprovider = CSRFMetadataProvider()

    form = FriendlyFormPlugin(login_form_url,
                              login_handler,
                              post_login_url,
                              logout_handler,
                              post_logout_url,
                              rememberer_name='fasident',
                              charset='utf-8')

    form.classifications = { IIdentifier: ['browser'],
                             IChallenger: ['browser'] } # only for browser

    basicauth = BasicAuthPlugin('repoze.who')

    identifiers = [('form', form), ('fasident', faswho), ('basicauth', basicauth)]
    authenticators = [('fasauth', faswho)]
    challengers = [('form', form), ('basicauth', basicauth)]
    mdproviders = [('fasmd', faswho), ('csrfmd', csrf_mdprovider)]

    if os.environ.get('FAS_WHO_LOG'):
        log_stream = sys.stdout

    app = CSRFProtectionMiddleware(app)
    app = PluggableAuthenticationMiddleware(
            app,
            identifiers,
            authenticators,
            challengers,
            mdproviders,
            fas_request_classifier,
            default_challenge_decider,
            log_stream = log_stream,
            )

    return app

class FASWhoPlugin(object):

    def __init__(self, url, insecure=False, session_cookie='tg-visit',
            ssl_cookie=True, httponly=True):
        self.url = url
        self.insecure = insecure
        self.fas = FasProxyClient(url, insecure=insecure)
        self.session_cookie = session_cookie
        self.ssl_cookie = ssl_cookie
        self.httponly = httponly
        self._session_cache = {}
        self._metadata_plugins = []

        for entry in pkg_resources.iter_entry_points(
                'fas.repoze.who.metadata_plugins'):
            self._metadata_plugins.append(entry.load())

    def _retrieve_user_info(self, environ, auth_params=None):
        ''' Retrieve information from fas and cache the results.

            We need to retrieve the user fresh every time because we need to
            know that the password hasn't changed or the session_id hasn't
            been invalidated by the user logging out.
        '''
        if not auth_params:
            return None

        user_data = self.fas.get_user_info(auth_params)

        if not user_data:
            self.forget(environ, None)
            return None
        if isinstance(user_data, tuple):
            user_data = list(user_data)

        # Set session_id in here so it can be found by other plugins
        user_data[1]['session_id'] = user_data[0]

        # we don't define permissions since we don't have any peruser data
        # though other services may wish to add another metadata plugin to do
        # so
        if not user_data[1].has_key('permissions'):
            user_data[1]['permissions'] = set()

        # we keep the approved_memberships list because there is also an
        # unapproved_membership field.  The groups field is for repoze.who
        # group checking and may include other types of groups besides
        # memberships in the future (such as special fedora community groups)

        groups = set()
        for g in user_data[1]['approved_memberships']:
            groups.add(g['name'])

        user_data[1]['groups'] = groups
        # If we have information on the user, cache it for later
        fas_cache.set_value(user_data[1]['username'], user_data,
                expiretime=FAS_CACHE_TIMEOUT)
        return user_data

    def identify(self, environ):
        '''Extract information to identify a user

        Retrieve either a username and password or a session_id that can be
        passed on to FAS to authenticate the user.
        '''
        log.info(b_('in identify()'))

        # friendlyform compat
        if not 'repoze.who.logins' in environ:
            environ['repoze.who.logins'] = 0

        req = webob.Request(environ, charset='utf-8')
        cookie = req.cookies.get(self.session_cookie)

        # This is compatible with TG1 and it gives us a way to authenticate
        # a user without making two requests
        query = req.GET
        form = Bunch(req.POST)
        form.update(query)
        if form.get('login', None) == 'Login' and \
                'user_name' in form and \
                'password' in form:
            identity = {'login': form['user_name'], 'password': form['password']}
            keys = ('login', 'password', 'user_name')
            for k in keys:
                if k in req.GET:
                    del(req.GET[k])
                if k in req.POST:
                    del(req.POST[k])
            return identity

        if cookie is None:
            return None

        log.info(b_('Request identify for cookie %(cookie)s') %
                {'cookie': to_bytes(cookie)})
        try:
            user_data = self._retrieve_user_info(environ,
                    auth_params={'session_id': cookie})
        except Exception, e: # pylint:disable-msg=W0703
            # For any exceptions, returning None means we failed to identify
            log.warning(e)
            return None

        if not user_data:
            return None

        # Preauthenticated
        identity = {'repoze.who.userid': user_data[1]['username'],
                'login': user_data[1]['username'],
                'password': user_data[1]['password']}
        return identity

    def remember(self, environ, identity):
        log.info(b_('In remember()'))
        req = webob.Request(environ)
        result = []

        user_data = fas_cache.get_value(identity['login'])
        try:
            session_id = user_data[0]
        except Exception, e:
            return None

        set_cookie = ['%s=%s; Path=/;' % (self.session_cookie, session_id)]
        if self.ssl_cookie:
            set_cookie.append('Secure')
        if self.httponly:
            set_cookie.append('HttpOnly')
        set_cookie = '; '.join(set_cookie)
        result.append(('Set-Cookie', set_cookie))
        return result

    def forget(self, environ, identity):
        log.info(b_('In forget()'))
        # return a expires Set-Cookie header
        req = webob.Request(environ)

        user_data = fas_cache.get_value(identity['login'])
        try:
            session_id = user_data[0]
        except Exception:
            return None

        log.info(b_('Forgetting login data for cookie %(s_id)s') %
                {'s_id': to_bytes(session_id)})

        self.fas.logout(session_id)

        result = []
        fas_cache.remove_value(key=identity['login'])
        expired = '%s=\'\'; Path=/; Expires=Sun, 10-May-1971 11:59:00 GMT'\
                % self.session_cookie
        result.append(('Set-Cookie', expired))
        return result

    # IAuthenticatorPlugin
    def authenticate(self, environ, identity):
        log.info(b_('In authenticate()'))

        def set_error(msg):
            log.info(msg)
            err = 1
            environ['FAS_AUTH_ERROR'] = err
            # HTTPForbidden ?
            err_app = HTTPFound(err_goto + '?' +
                                'came_from=' + quote_plus(came_from))
            environ['repoze.who.application'] = err_app


        err_goto = '/login'
        default_came_from = '/'
        if 'SCRIPT_NAME' in environ:
            sn = environ['SCRIPT_NAME']
            err_goto = sn + err_goto
            default_came_from = sn + default_came_from

        query = parse_dict_querystring(environ)
        form = parse_formvars(environ)
        form.update(query)
        came_from = form.get('came_from', default_came_from)

        try:
            auth_params = {'username': identity['login'],
                    'password': identity['password']}
        except KeyError:
            try:
                auth_params = {'session_id': identity['session_id']}
            except:
                # On error we return None which means that auth failed
                set_error(b_('Parameters for authenticating not found'))
                return None

        try:
            user_data = self._retrieve_user_info(environ, auth_params)
        except AuthError, e:
            set_error(b_('Authentication failed: %s') % exception_to_bytes(e))
            log.warning(e)
            return None
        except Exception, e:
            set_error(b_('Unknown auth failure: %s') % exception_to_bytes(e))
            return None

        if user_data:
            try:
                del user_data[1]['password']
                environ['CSRF_AUTH_SESSION_ID'] = user_data[0]
                return user_data[1]['username']
            except ValueError:
                set_error(b_('user information from fas not in expected format!'))
                return None
            except Exception, e:
                pass
        set_error(b_('An unknown error happened when trying to log you in.'
                ' Please try again.'))
        return None

    def add_metadata(self, environ, identity):
        log.info(b_('In add_metadata'))
        req = webob.Request(environ)

        if identity.get('error'):
            log.info(b_('Error exists in session, no need to set metadata'))
            return 'error'

        plugin_user_info = {}
        for plugin in self._metadata_plugins:
            plugin(plugin_user_info)
        identity.update(plugin_user_info)
        del plugin_user_info

        user = identity.get('repoze.who.userid')
        (session_id, user_info) = fas_cache.get_value(key=user,
                expiretime=FAS_CACHE_TIMEOUT)

        #### FIXME: Deprecate this line!!!
        # If we make a new version of fas.who middleware, get rid of saving
        # user information directly into identity.  Instead, save it into
        # user, as is done below
        identity.update(user_info)

        identity['userdata'] = user_info
        identity['user'] = Bunch()
        identity['user'].created = user_info['creation']
        identity['user'].display_name = user_info['human_name']
        identity['user'].email_address = user_info['email']
        identity['user'].groups = user_info['groups']
        identity['user'].password = None
        identity['user'].permissions = user_info['permissions']
        identity['user'].user_id = user_info['id']
        identity['user'].user_name = user_info['username']
        identity['groups'] = user_info['groups']
        identity['permissions'] = user_info['permissions']

        if 'repoze.what.credentials' not in environ:
            environ['repoze.what.credentials'] = {}

        environ['repoze.what.credentials']['groups'] = user_info['groups']
        environ['repoze.what.credentials']['permissions'] = user_info['permissions']

        # Adding the userid:
        userid = identity['repoze.who.userid']
        environ['repoze.what.credentials']['repoze.what.userid'] = userid

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, id(self))
