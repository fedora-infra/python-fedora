# -*- coding: utf-8 -*-
#
# Copyright (C) 2007-2008  Red Hat, Inc.
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
'''**Deprecated** Use jsonfasprovider2 instead a it provides CSRF protection.

This plugin provides integration with the Fedora Account System using
:term:`JSON` calls.


.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. moduleauthor:: Ricky Zhou <ricky@fedoraproject.org>
'''

from cherrypy import response
from turbogears import config, identity
from kitchen.text.converters import to_bytes
from kitchen.pycompat24 import sets
sets.add_builtin_set()

from fedora.client import BaseClient, FedoraServiceError

from fedora import b_, __version__

import crypt

import logging
log = logging.getLogger('turbogears.identity.safasprovider')

class JsonFasIdentity(BaseClient):
    '''
    Associate an identity with a person in the auth system.
    '''
    cookie_name = config.get('visit.cookie.name', 'tg-visit')
    fas_url = config.get('fas.url', 'https://admin.fedoraproject.org/accounts/')
    useragent = 'JsonFasIdentity/%s' % __version__
    cache_session = False

    def __init__(self, visit_key, user=None, username=None, password=None):
        if user:
            self._user = user
            self._groups = frozenset(
                    [g['name'] for g in user['approved_memberships']]
                    )
        self.visit_key = visit_key
        if visit_key:
            # Set the cookie to the user's tg_visit key before requesting
            # authentication.  That way we link the two together.
            session_id = visit_key
        else:
            session_id = None

        debug = config.get('jsonfas.debug', False)
        super(JsonFasIdentity, self).__init__(self.fas_url,
                useragent=self.useragent, debug=debug,
                username=username, password=password,
                session_id=session_id, cache_session=self.cache_session)

        if self.debug:
            import inspect
            caller = inspect.getouterframes(inspect.currentframe())[1][3]
            log.debug('JsonFasIdentity.__init__ caller: %s' % caller)

        response.simple_cookie[self.cookie_name] = visit_key

        # Send a request so that we associate the visit_cookie with the user
        self.send_request('', auth=True)
        log.debug('Leaving JsonFasIdentity.__init__')

    def send_request(self, method, req_params=None, auth=False):
        '''
        Make an HTTP Request to a server method.

        We need to override the send_request provided by ``BaseClient`` to
        keep the visit_key in sync.
        '''
        log.debug('Entering jsonfas send_request')
        if self.session_id != self.visit_key:
            # When the visit_key changes (because the old key had expired or
            # been deleted from the db) change the visit_key in our variables
            # and the session cookie to be sent back to the client.
            self.visit_key = self.session_id
            response.simple_cookie[self.cookie_name] = self.visit_key
        log.debug('Leaving jsonfas send_request')
        return super(JsonFasIdentity, self).send_request(method,
                req_params=req_params, auth=auth)

    def _get_user(self):
        '''Retrieve information about the user from cache or network.'''
        # pylint: disable-msg=W0704
        try:
            return self._user
        except AttributeError:
            # User hasn't already been set
            pass
        # pylint: enable-msg=W0704

        if self.debug:
            import inspect
            caller = inspect.getouterframes(inspect.currentframe())[1][3]
            log.debug('JSONFASPROVIDER.send_request caller: %s' % caller)

        # Attempt to load the user. After this code executes, there *WILL* be
        # a _user attribute, even if the value is None.
        # Query the account system URL for our given user's sessionCookie
        # FAS returns user and group listing
        # pylint: disable-msg=W0702
        try:
            data = self.send_request('user/view', auth=True)
        except:
            # Any errors have to result in no user being set.  The rest of the
            # framework doesn't know what to do otherwise.
            self._user = None
            return None
        # pylint: enable-msg=W0702
        if not data['person']:
            self._user = None
            return None
        self._user = data['person']
        self._groups = frozenset(
                [g['name'] for g in data['person']['approved_memberships']]
                )
        return self._user
    user = property(_get_user)

    def _get_user_name(self):
        '''Return the username for the user.'''
        if self.debug:
            import inspect
            caller = inspect.getouterframes(inspect.currentframe())[1][3]
            log.debug('JsonFasProvider._get_user_name caller: %s' % caller)

        if not self.user:
            return None
        return self.user['username']
    user_name = property(_get_user_name)

    def _get_anonymous(self):
        '''Return True if there's no user logged in.'''
        return not self.user
    anonymous = property(_get_anonymous)

    def _get_display_name(self):
        '''Return the user's display name.'''
        if not self.user:
            return None
        return self.user['human_name']
    display_name = property(_get_display_name)

    def _get_groups(self):
        '''Return the groups that a user is a member of.'''
        try:
            return self._groups
        except AttributeError:
            # User and groups haven't been returned.  Since the json call
            # returns both user and groups, this is set at user creation time.
            self._groups = frozenset()
        return self._groups
    groups = property(_get_groups)

    def logout(self):
        '''
        Remove the link between this identity and the visit.
        '''
        if not self.visit_key:
            return
        # Call Account System Server logout method
        self.send_request('logout', auth=True)

class JsonFasIdentityProvider(object):
    '''
    IdentityProvider that authenticates users against the fedora account system
    '''
    def __init__(self):
        # Default encryption algorithm is to use plain text passwords
        algorithm = config.get('identity.saprovider.encryption_algorithm', None)
        # pylint: disable-msg=W0212
        # TG does this so we shouldn't get rid of it.
        self.encrypt_password = lambda pw: \
                                    identity._encrypt_password(algorithm, pw)

    def create_provider_model(self):
        '''
        Create the database tables if they don't already exist.
        '''
        # No database tables to create because the db is behind the FAS2
        # server
        pass

    def validate_identity(self, user_name, password, visit_key):
        '''
        Look up the identity represented by user_name and determine whether the
        password is correct.

        Must return either None if the credentials weren't valid or an object
        with the following properties:

            :user_name: original user name
            :user: a provider dependant object (TG_User or similar)
            :groups: a set of group IDs
            :permissions: a set of permission IDs
        '''
        # pylint: disable-msg=R0201
        # TG identity providers have this method so we can't get rid of it.
        try:
            user = JsonFasIdentity(visit_key, username = user_name,
                    password = password)
        except FedoraServiceError, e:
            log.warning(b_('Error logging in %(user)s: %(error)s') % {
                'user': to_bytes(user_name), 'error': to_bytes(e)})
            return None

        return user

    def validate_password(self, user, user_name, password):
        '''
        Check the supplied user_name and password against existing credentials.
        Note: user_name is not used here, but is required by external
        password validation schemes that might override this method.
        If you use SqlAlchemyIdentityProvider, but want to check the passwords
        against an external source (i.e. PAM, LDAP, Windows domain, etc),
        subclass SqlAlchemyIdentityProvider, and override this method.

        :arg user: User information.  Not used.
        :arg user_name: Given username.
        :arg password: Given, plaintext password.
        :returns: True if the password matches the username.  Otherwise False.
            Can return False for problems within the Account System as well.
        '''
        # pylint: disable-msg=W0613,R0201
        # TG identity providers take user_name in case an external provider
        # needs it so we can't get rid of it.
        # TG identity providers have this method so we can't get rid of it.
        return user.password == crypt.crypt(password, user.password)

    def load_identity(self, visit_key):
        '''Lookup the principal represented by visit_key.

        :arg visit_key: The session key for whom we're looking up an identity.
        :returns: an object with the following properties:

            :user_name: original user name
            :user: a provider dependant object (TG_User or similar)
            :groups: a set of group IDs
            :permissions: a set of permission IDs
        '''
        # pylint: disable-msg=R0201
        # TG identity providers have this method so we can't get rid of it.
        return JsonFasIdentity(visit_key)

    def anonymous_identity(self):
        '''
        Must return an object with the following properties:

            :user_name: original user name
            :user: a provider dependant object (TG_User or similar)
            :groups: a set of group IDs
            :permissions: a set of permission IDs
        '''
        # pylint: disable-msg=R0201
        # TG identity providers have this method so we can't get rid of it.
        return JsonFasIdentity(None)

    def authenticated_identity(self, user):
        '''
        Constructs Identity object for user that has no associated visit_key.
        '''
        # pylint: disable-msg=R0201
        # TG identity providers have this method so we can't get rid of it.
        return JsonFasIdentity(None, user)
