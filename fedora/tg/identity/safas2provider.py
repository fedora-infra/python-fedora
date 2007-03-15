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
from fedora.accounts.fasLDAP import UserAccount, Person, Groups

from turbogears.identity.saprovider import *
from turbogears import config
from fedora.accounts.tgfas2 import VisitIdentity
from fedora.accounts.fas2 import AuthError

log = logging.getLogger(__name__)

visit_identity_class = None

class FASUser(object):
    def __init__(self, user, groupList):
        self.user_id = user.userName
        self.user_name = user.userName
        self.user = user
        self.groups = groupList
        self.permissions = None
        self.display_name = user.givenName

class FASGroup(object):
    def __init__(self, group):
        self.group_id = group.cn
        self.group_name = group.cn
        self.display_name = group.cn
        self.group = group

class SaFasIdentity(SqlAlchemyIdentity):
    def __init__(self, visit_key, user=None):
        super(SaFasIdentity, self).__init__(visit_key, user)

    def _get_user(self):
        try:
            return self._user
        except AttributeError:
            # User hasn't been set yet
            pass
        visit = visit_identity_class.get_by(visit_key = self.visit_key)
        if not visit:
            self._user = None
            return None
        user = Person.byUserName(visit.user_id)
        groups = Groups.byUserName(user.userName)
        groupList = []
        for group in groups.items():
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

class SaFas2IdentityProvider(SqlAlchemyIdentityProvider):
    '''
    IdentityProvider that authenticates users against the fedora account system
    '''
    def __init__(self):
        global visit_identity_class
        visit_identity_class_path = config.get("identity.saprovider.model.visit", None)
        log.info("Loading: %s", visit_identity_class_path)
        visit_identity_class = load_class(visit_identity_class_path)

    def validate_identity(self, user_name, password, visit_key):
        visit_identity_class.mapper.get_session().flush()
        visit_identity_class.mapper.get_session().clear()

        user = Person.byUserName(user_name)

        try:
            verified = self.validate_password(user, user_name, password)
        except AuthError, e:
            log.warning(e)
            return None
        if not verified:
            log.warning('Passwords do not match for user: %s', user_name)
            return None

        log.info("Login successful for %s" % user_name)

        link = visit_identity_class.get_by(visit_key=visit_key)
        if not link:
            link = visit_identity_class(visit_key=visit_key, user_id=user_name)
            visit_identity_class.mapper.get_session().save(link)
        else:
            link.user_id = user_name
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
            result = Person.auth(user_name, password)
        except Exception, e:
            log.warning('AccountSystem threw an exception: %s', e)
            return False
        return True

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
