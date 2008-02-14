# -*- coding: utf-8 -*-
#
# Copyright © 2007  Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing to use, modify,
# copy, or redistribute it subject to the terms and conditions of the GNU
# General Public License v.2.  This program is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY expressed or implied, including the
# implied warranties of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.  You should have
# received a copy of the GNU General Public License along with this program;
# if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA. Any Red Hat trademarks that are
# incorporated in the source code or documentation are not subject to the GNU
# General Public License and may only be used or replicated with the express
# permission of Red Hat, Inc.
#
# Red Hat Author(s): Toshio Kuratomi <tkuratom@redhat.com>
#

'''
This plugin provides authentication of passwords against the Fedora Account
System.
'''

import logging

from sqlalchemy.orm import class_mapper
from turbogears.identity.saprovider import SqlAlchemyIdentity, \
        SqlAlchemyIdentityProvider
from turbogears import config
from turbogears.util import load_class
from turbogears.database import session

from fedora.accounts.fas import AccountSystem
from fedora.accounts.tgfas import VisitIdentity
from fedora.accounts.fas import AuthError
from fedora.accounts.fas import DBError

import gettext
t = gettext.translation('python-fedora', '/usr/share/locale', fallback=True)
_ = t.ugettext

log = logging.getLogger('turbogears.identity.safasprovider')

visit_identity_class = None
fas = AccountSystem()

class FASUser(object):
    def __init__(self, user, groupList):
        self.user_id = user['id']
        self.user_name = user['username']
        self.user = user
        self.groups = groupList
        self.permissions = None
        self.display_name = user['human_name']

    def __json__(self):
        return {'user_id': self.user_id,
                'user_name': self.user_name,
                'groups': self.groups,
                'permissions': self.permissions,
                'display_name': self.display_name
                }

class FASGroup(object):
    def __init__(self, group):
        self.group_id = group['id']
        self.group_name = group['name']
        self.display_name = group['name']

    def __json__(self):
        return {'group_id' : self.group_id,
                'group_name': self.group_name,
                'display_name': self.display_name
                }

class SaFasIdentity(SqlAlchemyIdentity):
    def __init__(self, visit_key, user=None):
        super(SaFasIdentity, self).__init__(visit_key, user)

    def _get_user(self):
        try:
            return self._user
        except AttributeError:
            # User hasn't been set yet
            pass

        # If the user isn't logged in or we are unable to get information
        # about them from the fas database, return empty None
        visit = visit_identity_class.query.filter_by(visit_key = self.visit_key).first()
        if not visit:
            self._user = None
            return None
        try:
            user, groups = fas.get_user_info(visit.user_id)
        except DBError:
            self._user = None
            return None

        groupList = []
        for group in groups:
            groupList.append(FASGroup(group))
        # Construct a user from fas information
        self._user = FASUser(user, groupList)
        return self._user
    user = property(_get_user)

    # Copied verbatim from saprovider.py.  Because this uses a global variable
    # we cannot depend on inheritance to make a usable function.
    def logout(self):
        '''
        Remove the link between this identity and the visit.
        '''
        if not self.visit_key:
            return
        try:
            visit = visit_identity_class.query.filter_by(visit_key=self.visit_key).first()
            session.delete(visit)
            # Clear the current identity
            anon = SqlAlchemyIdentity(None,None)
            identity.set_current_identity(anon)
        except:
            pass
        else:
            session.flush()

class SaFasIdentityProvider(SqlAlchemyIdentityProvider):
    '''
    IdentityProvider that authenticates users against the fedora account system
    '''
    def __init__(self):
        global visit_identity_class
        visit_identity_class_path = config.get("identity.saprovider.model.visit", None)
        log.info(_("Loading: %(visitmod)s") % \
                {'visitmod': visit_identity_class_path})
        visit_identity_class = load_class(visit_identity_class_path)

    def create_provider_model(self):
        class_mapper(visit_identity_class).local_table.create(checkfirst=True)

    def validate_identity(self, user_name, password, visit_key):
        '''
        Look up the identity represented by user_name and determine whether the
        password is correct.

        Must return either None if the credentials weren't valid or an object
        with the following properties:
            user_name: original user name
            user: a provider dependant object (TG_User or similar)
            groups: a set of group IDs
            permissions: a set of permission IDs
        '''
        try:
            verified = fas.verify_user_pass(user_name, password)
        except (AuthError, DBError), e:
            log.warning(_('Error %(err)s for %(user)s') % \
                    {'err': e, 'user': user_name})
            return None
        if not verified:
            log.warning(_('Passwords do not match for user: %(user)s') % \
                    {'user': user_name})
            return None

        log.info(_('Login successful for %(user)s') % {'user': user_name})

        try:
            userId = fas.get_user_id(user_name)
        except DBError, e:
            log.warning(_('Error %(err)s for %(user)s') \
                    % {'err': e, 'user': user_name})
            return None

        link = visit_identity_class.query.filter_by(visit_key=visit_key).first()
        if not link:
            link = visit_identity_class()
            link.visit_key = visit_key
            link.user_id = userId
        else:
            link.user_id = userId
        session.flush()
        return SaFasIdentity(visit_key)

    def validate_password(self, user, user_name, password):
        '''Verify user and password match in the Account System.

        Arguments:
        :user: User information.  Not used.
        :user_name: Given username.
        :password: Given, plaintext password.

        Returns: True if the password matches the username.  Otherwise False.
          Can return False for problems within the Account System as well.
        '''
        try:
            result = fas.verify_user_pass(user_name, password)
        except (AuthError, DBError), e:
            log.warning(_('AccountSystem threw an exception: %(err)s for' \
                    ' %(user)s') % {'err': e, 'user': user_name})
            return False
        return result

    def load_identity(self, visit_key):
        '''Lookup the principal represented by visit_key.

        Arguments:
        :visit_key: The session key for whom we're looking up an identity.

        Returns: None if there is no principal for the given user ID.  Otherwise
          an object with the following properties:
            :user_name: original user name
            :user: a provider dependant object (TG_User or similar)
            :groups: a set of group IDs
            :permissions: a set of permission IDs
        '''
        return SaFasIdentity(visit_key)

    def anonymous_identity(self):
        return SaFasIdentity(None)

    def authenticated_identity(self, user):
        return SaFasIdentity(None, user)
