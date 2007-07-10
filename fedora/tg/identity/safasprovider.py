# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

'''
This plugin provides authentication of passwords against the Fedora Account
System.
'''

import logging
from fedora.accounts.fas import AccountSystem

from turbogears.identity.saprovider import *
from turbogears import config
from fedora.accounts.tgfas import VisitIdentity
from fedora.accounts.fas import AuthError
from fedora.accounts.fas import DBError

log = logging.getLogger(__name__)

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

        # If the user isn't logged in or we are unable to get information from
        # about them from the fas database, return empty None
        try:
            visit = visit_identity_class.get_by(visit_key = self.visit_key)
        except:
            return None
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

    ### FIXME: This is unnecessary once TG Bug #1238 is resolved.
    # Basically, we do not want to refer to the app-wide session directly as
    # we could be using a site-wide session.  Use the session associated with
    # the mapper for the visit class instead.
    def logout(self):
        '''
        Remove the link between this identity and the visit.
        '''
        if not self.visit_key:
            return
        try:
            visit = visit_identity_class.get_by(visit_key=self.visit_key)
            visit.delete()
            # Clear the current identity
            anon = SaFasIdentity(None,None)
            identity.set_current_identity(anon)
        except:
            pass
        else:
            visit_identity_class.mapper.get_session().flush()

class SaFasIdentityProvider(SqlAlchemyIdentityProvider):
    '''
    IdentityProvider that authenticates users against the fedora account system
    '''
    def __init__(self):
        global visit_identity_class
        visit_identity_class_path = config.get("identity.saprovider.model.visit", None)
        log.info("Loading: %s", visit_identity_class_path)
        visit_identity_class = load_class(visit_identity_class_path)

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
        visit_identity_class.mapper.get_session().flush()
        visit_identity_class.mapper.get_session().clear()
        try:
            verified = fas.verify_user_pass(user_name, password)
        except (AuthError, DBError), e:
            log.warning('Error %s for %s' % (e, user_name))
            return None
        if not verified:
            log.warning('Passwords do not match for user: %s', user_name)
            return None

        log.info("Login successful for %s" % user_name)

        try:
            userId = fas.get_user_id(user_name)
        except DBError, e:
            log.warning('Error %s for %s' % (e, user_name))
            return None

        link = visit_identity_class.get_by(visit_key=visit_key)
        if not link:
            link = visit_identity_class(visit_key=visit_key, user_id = userId)
            visit_identity_class.mapper.get_session().save(link)
        else:
            link.user_id = userId
        visit_identity_class.mapper.get_session().flush()
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
            log.warning('AccountSystem threw an exception: %s for %s', (e,
                user_name))
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
