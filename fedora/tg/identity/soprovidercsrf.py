# -*- coding: utf-8 -*-
#
# Copyright (C) 2009  Red Hat, Inc.
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
# Adapted from code in the TurboGears project licensed under the MIT license.
#
'''
This plugin provides authentication from a database using sqlobject.  In
addition to the standard stuff provided by the TurboGears soprovider, it
adds a csrf_token attribute that can be used to protect the server from
csrf attacks.

.. versionadded:: 0.3.14


.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''
from datetime import datetime

try:
    from hashlib import sha1 as hash_constructor
except ImportError:
    from sha import new as hash_constructor


from sqlobject import SQLObject, SQLObjectNotFound, RelatedJoin, \
        DateTimeCol, IntCol, StringCol, UnicodeCol
from sqlobject.inheritance import InheritableSQLObject

import warnings
import logging
log = logging.getLogger("turbogears.identity.soprovider")

import cherrypy
import turbogears
from turbogears import identity
from turbogears.database import PackageHub
from turbogears.util import load_class
from turbogears.identity import set_login_attempted
from turbojson.jsonify import jsonify_sqlobject, jsonify

hub = PackageHub("turbogears.identity")
__connection__ = hub

try:
    set, frozenset
except NameError:  # Python 2.3
    from sets import Set as set, ImmutableSet as frozenset


def to_db_encoding(s, encoding):
    if isinstance(s, str):
        pass
    elif hasattr(s, '__unicode__'):
        s = unicode(s)
    if isinstance(s, unicode):
        s = s.encode(encoding)
    return s


class DeprecatedAttr(object):
    def __init__(self, old_name, new_name):
        self.old_name = old_name
        self.new_name = new_name

    def __get__(self, obj, type=None):
        warnings.warn("%s has been deprecated in favour of %s" %
            (self.old_name, self.new_name), DeprecationWarning)
        return getattr(obj, self.new_name)

    def __set__(self, obj, value):
        warnings.warn( "%s has been deprecated in favour of %s" %
            (self.old_name, self.new_name), DeprecationWarning)
        return setattr(obj, self.new_name, value)


# Global class references --
# these will be set when the provider is initialised.
user_class = None
group_class = None
permission_class = None
visit_class = None


class SqlObjectCsrfIdentity(object):
    """Identity that uses a model from a database (via SQLObject)."""

    def __init__(self, visit_key=None, user=None):
        # The reason we have both _retrieved_user and _user is this:
        # _user is set if both the user is authenticated and a csrf_token is
        # present.
        # _retrieved_user actually caches the user info from the server.
        # Sometimes we have to determine if a user is only lacking a token,
        # then retrieved_user comes in handy.
        self._retrieved_user = None
        self.visit_key = visit_key
        if user:
            self._user = user
            self._user_retrieved = user
            if visit_key is not None:
                self.login()

    def __retrieve_user(self):
        '''Attempt to load the user from the visit_key

        :returns: a user or None
        '''
        if self._retrieved_user:
            return self._retrieved_user

        # Retrieve the user info from the db
        visit = self.visit_link
        if not visit:
            return None
        try:
            self._retrieved_user = user_class.get(visit.user_id)
        except SQLObjectNotFound:
            log.warning("No such user with ID: %s", visit.user_id)
            self._retrieved_user = None
        return self._retrieved_user

    def _get_user(self):
        """Get user instance for this identity."""
        try:
            return self._user
        except AttributeError:
            # User hasn't already been set
            pass
        # Attempt to load the user. After this code executes, there *will* be
        # a _user attribute, even if the value is None.
        visit = self.visit_link
        if not visit:
            # No visit, no user
            self._user = None
        else:
            # Unless we were given the user_name and password to login on
            # this request, a CSRF token is required
            if (not '_csrf_token' in cherrypy.request.params or
                    cherrypy.request.params['_csrf_token'] !=
                    hash_constructor(self.visit_key).hexdigest()):
                log.info("Bad _csrf_token")
                if '_csrf_token' in cherrypy.request.params:
                    log.info("visit: %s token: %s" % (self.visit_key,
                        cherrypy.request.params['_csrf_token']))
                else:
                    log.info('No _csrf_token present')
                cherrypy.request.fas_identity_failure_reason = 'bad_csrf'
                self._user = None
        try:
            return self._user
        except AttributeError:
            # User hasn't already been set
            # Attempt to load the user.  After this code executes, there
            # *will* be a _user attribute, even if the value is None.
            self._user = self.__retrieve_user()
        return self._user
    user = property(_get_user)

    def _get_token(self):
        '''Get the csrf token for this identity'''
        if self.visit_key:
            return hash_constructor(self.visit_key).hexdigest()
        else:
            return ''
    csrf_token = property(_get_token)

    def _get_user_name(self):
        """Get user name of this identity."""
        if not self.user:
            return None
        return self.user.user_name
    user_name = property(_get_user_name)

    def _get_user_id(self):
        """Get user id of this identity."""
        if not self.user:
            return None
        return self.user.id
    user_id = property(_get_user_id)

    def _get_anonymous(self):
        """Return true if not logged in."""
        return not self.user
    anonymous = property(_get_anonymous)

    def _get_only_token(self):
        '''
        In one specific instance in the login template we need to know whether
        an anonymous user is just lacking a token.
        '''
        if self.__retrieve_user():
            # user is valid, just the token is missing
            return True

        # Else the user still has to login
        return False
    only_token = property(_get_only_token)

    def _get_permissions(self):
        """Get set of permission names of this identity."""
        try:
            return self._permissions
        except AttributeError:
            # Permissions haven't been computed yet
            pass
        if not self.user:
            self._permissions = frozenset()
        else:
            self._permissions = frozenset(
                [p.permission_name for p in self.user.permissions])
        return self._permissions
    permissions = property(_get_permissions)

    def _get_groups(self):
        """Get set of group names of this identity."""
        try:
            return self._groups
        except AttributeError:
            # Groups haven't been computed yet
            pass
        if not self.user:
            self._groups = frozenset()
        else:
            self._groups = frozenset([g.group_name for g in self.user.groups])
        return self._groups
    groups = property(_get_groups)

    def _get_group_ids(self):
        """Get set of group IDs of this identity."""
        try:
            return self._group_ids
        except AttributeError:
            # Groups haven't been computed yet
            pass
        if not self.user:
            self._group_ids = frozenset()
        else:
            self._group_ids = frozenset([g.id for g in self.user.groups])
        return self._group_ids
    group_ids = property(_get_group_ids)

    def _get_visit_link(self):
        """Get the visit link to this identity."""
        if self.visit_key is None:
            return None
        try:
            return visit_class.by_visit_key(self.visit_key)
        except SQLObjectNotFound:
            return None
    visit_link = property(_get_visit_link)

    def _get_login_url(self):
        """Get the URL for the login page."""
        return identity.get_failure_url()
    login_url = property(_get_login_url)

    def login(self):
        """Set the link between this identity and the visit."""
        visit = self.visit_link
        if visit:
            visit.user_id = self._user.id
        else:
            visit = visit_class(visit_key=self.visit_key, user_id=self._user.id)

    def logout(self):
        """Remove the link between this identity and the visit."""
        visit = self.visit_link
        if visit:
            visit.destroySelf()
        # Clear the current identity
        identity.set_current_identity(SqlObjectCsrfIdentity())


class SqlObjectCsrfIdentityProvider(object):
    """IdentityProvider that uses a model from a database (via SQLObject)."""

    def __init__(self):
        super(SqlObjectCsrfIdentityProvider, self).__init__()
        get = turbogears.config.get

        global user_class, group_class, permission_class, visit_class

        user_class_path = get("identity.soprovider.model.user",
            __name__ + ".TG_User")
        user_class = load_class(user_class_path)
        if user_class:
            log.info("Succesfully loaded \"%s\"" % user_class_path)
        try:
            self.user_class_db_encoding = \
                user_class.sqlmeta.columns['user_name'].dbEncoding
        except (KeyError, AttributeError):
            self.user_class_db_encoding = 'UTF-8'
        group_class_path = get("identity.soprovider.model.group",
            __name__ + ".TG_Group")
        group_class = load_class(group_class_path)
        if group_class:
            log.info("Succesfully loaded \"%s\"" % group_class_path)

        permission_class_path = get("identity.soprovider.model.permission",
            __name__ + ".TG_Permission")
        permission_class = load_class(permission_class_path)
        if permission_class:
            log.info("Succesfully loaded \"%s\"" % permission_class_path)

        visit_class_path = get("identity.soprovider.model.visit",
            __name__ + ".TG_VisitIdentity")
        visit_class = load_class(visit_class_path)
        if visit_class:
            log.info("Succesfully loaded \"%s\"" % visit_class_path)

        # Default encryption algorithm is to use plain text passwords
        algorithm = get("identity.soprovider.encryption_algorithm", None)
        self.encrypt_password = lambda pw: \
            identity._encrypt_password(algorithm, pw)

    def create_provider_model(self):
        """Create the database tables if they don't already exist."""
        try:
            hub.begin()
            user_class.createTable(ifNotExists=True)
            group_class.createTable(ifNotExists=True)
            permission_class.createTable(ifNotExists=True)
            visit_class.createTable(ifNotExists=True)
            hub.commit()
            hub.end()
        except KeyError:
            log.warning("No database is configured:"
                " SqlObjectCsrfIdentityProvider is disabled.")
            return

    def validate_identity(self, user_name, password, visit_key):
        """Validate the identity represented by user_name using the password.

        Must return either None if the credentials weren't valid or an object
        with the following properties:
            user_name: original user name
            user: a provider dependant object (TG_User or similar)
            groups: a set of group names
            permissions: a set of permission names

        """
        try:
            user_name = to_db_encoding(user_name, self.user_class_db_encoding)
            user = user_class.by_user_name(user_name)
            if not self.validate_password(user, user_name, password):
                log.info("Passwords don't match for user: %s", user_name)
                return None
            log.info("Associating user (%s) with visit (%s)",
                user_name, visit_key)
            return SqlObjectCsrfIdentity(visit_key, user)
        except SQLObjectNotFound:
            log.warning("No such user: %s", user_name)
            return None

    def validate_password(self, user, user_name, password):
        """Check the user_name and password against existing credentials.

        Note: user_name is not used here, but is required by external
        password validation schemes that might override this method.
        If you use SqlObjectCsrfIdentityProvider, but want to check the passwords
        against an external source (i.e. PAM, a password file, Windows domain),
        subclass SqlObjectCsrfIdentityProvider, and override this method.

        """
        return user.password == self.encrypt_password(password)

    def load_identity(self, visit_key):
        """Lookup the principal represented by user_name.

        Return None if there is no principal for the given user ID.

        Must return an object with the following properties:
            user_name: original user name
            user: a provider dependant object (TG_User or similar)
            groups: a set of group names
            permissions: a set of permission names

        """
        ident = SqlObjectCsrfIdentity(visit_key)
        if 'csrf_login' in cherrypy.request.params:
            cherrypy.request.params.pop('csrf_login')
            set_login_attempted(True)
        return ident

    def anonymous_identity(self):
        """Return anonymous identity.

        Must return an object with the following properties:
            user_name: original user name
            user: a provider dependant object (TG_User or similar)
            groups: a set of group names
            permissions: a set of permission names

        """
        return SqlObjectCsrfIdentity()

    def authenticated_identity(self, user):
        """Constructs Identity object for users with no visit_key."""
        return SqlObjectCsrfIdentity(user=user)


class TG_VisitIdentity(SQLObject):
    """A visit to your website."""
    class sqlmeta:
        table = "tg_visit_identity"

    visit_key = StringCol(length=40, alternateID=True,
        alternateMethodName="by_visit_key")
    user_id = IntCol()


class TG_Group(InheritableSQLObject):
    """An ultra-simple group definition."""
    class sqlmeta:
        table = "tg_group"

    group_name = UnicodeCol(length=16, alternateID=True,
        alternateMethodName="by_group_name")
    display_name = UnicodeCol(length=255)
    created = DateTimeCol(default=datetime.now)

    # Old names
    groupId = DeprecatedAttr("groupId", "group_name")
    displayName = DeprecatedAttr("displayName", "display_name")

    # collection of all users belonging to this group
    users = RelatedJoin("TG_User", intermediateTable="tg_user_group",
        joinColumn="group_id", otherColumn="user_id")

    # collection of all permissions for this group
    permissions = RelatedJoin("TG_Permission", joinColumn="group_id",
        intermediateTable="tg_group_permission",
        otherColumn="permission_id")

[jsonify.when('isinstance(obj, TG_Group)')]
def jsonify_group(obj):
    """Convert group to JSON."""
    result = jsonify_sqlobject(obj)
    result["users"] = [u.user_name for u in obj.users]
    result["permissions"] = [p.permission_name for p in obj.permissions]
    return result


class TG_User(InheritableSQLObject):
    """Reasonably basic User definition."""
    class sqlmeta:
        table = "tg_user"

    user_name = UnicodeCol(length=16, alternateID=True,
        alternateMethodName="by_user_name")
    email_address = UnicodeCol(length=255, alternateID=True,
        alternateMethodName="by_email_address")
    display_name = UnicodeCol(length=255)
    password = UnicodeCol(length=40)
    created = DateTimeCol(default=datetime.now)

    # Old attribute names
    userId = DeprecatedAttr("userId", "user_name")
    emailAddress = DeprecatedAttr("emailAddress", "email_address")
    displayName = DeprecatedAttr("displayName", "display_name")

    # groups this user belongs to
    groups = RelatedJoin("TG_Group", intermediateTable="tg_user_group",
        joinColumn="user_id", otherColumn="group_id")

    def _get_permissions(self):
        perms = set()
        for g in self.groups:
            perms = perms | set(g.permissions)
        return perms

    def _set_password(self, cleartext_password):
        """Run cleartext_password through the hash algorithm before saving."""
        try:
            hash = identity.current_provider.encrypt_password(
                    cleartext_password)
        except identity.exceptions.IdentityManagementNotEnabledException:
            # Creating identity provider just to encrypt password
            # (so we don't reimplement the encryption step).
            ip = SqlObjectCsrfIdentityProvider()
            hash = ip.encrypt_password(cleartext_password)
            if hash == cleartext_password:
                log.info("Identity provider not enabled,"
                    " and no encryption algorithm specified in config."
                    " Setting password as plaintext.")
        self._SO_set_password(hash)

    def set_password_raw(self, password):
        """Save the password as-is to the database."""
        self._SO_set_password(password)

[jsonify.when('isinstance(obj, TG_User)')]
def jsonify_user(obj):
    """Convert user to JSON."""
    result = jsonify_sqlobject(obj)
    del result['password']
    result["groups"] = [g.group_name for g in obj.groups]
    result["permissions"] = [p.permission_name for p in obj.permissions]
    return result


class TG_Permission(InheritableSQLObject):
    """Permissions for a given group."""
    class sqlmeta:
        table = "tg_permission"

    permission_name = UnicodeCol(length=16, alternateID=True,
        alternateMethodName="by_permission_name")
    description = UnicodeCol(length=255)

    # Old attributes
    permissionId = DeprecatedAttr("permissionId", "permission_name")

    groups = RelatedJoin("TG_Group", intermediateTable="tg_group_permission",
        joinColumn="permission_id", otherColumn="group_id")

[jsonify.when('isinstance(obj, TG_Permission)')]
def jsonify_permission(obj):
    """Convert permissions to JSON."""
    result = jsonify_sqlobject(obj)
    result["groups"] = [g.group_name for g in obj.groups]
    return result


def encrypt_password(cleartext_password):
    """Encrypt given cleartext password."""
    try:
        hash = identity.current_provider.encrypt_password(cleartext_password)
    except identity.exceptions.RequestRequiredException:
        # Creating identity provider just to encrypt password
        # (so we don't reimplement the encryption step).
        ip = SqlObjectCsrfIdentityProvider()
        hash = ip.encrypt_password(cleartext_password)
        if hash == cleartext_password:
            log.info("Identity provider not enabled, and no encryption "
                "algorithm specified in config. Setting password as plaintext.")
    return hash
