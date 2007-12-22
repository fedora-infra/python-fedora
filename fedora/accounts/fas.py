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

'''API to Access the Fedora Account System

This is an alternative python interface to the Fedora Accounts system.
The original website.py module has quite a few issues that we're attempting
to address here:

* We should be able to change from an SQL db to ldap without the consuming
  application being any the wiser.  website.py requires the app to track the
  database handle so that doesn't work well.
* An object oriented interface is preferable to the procedural interface that
  we had before.  Then we can hang onto the database handle and take care of
  authentication within the object.
* Separate out the session handling code from database retrieval code.  This
  will be required when we move to LDAP.
* Separate out the website template code.
* Use psycopg2 instead of pgdb for performance and features.
* Create a pool of connections so we can efficiently call the fas from multiple
  threads.
'''
__version__='0.1'

adminUserId = 100001

import psycopg2
import psycopg2.extras
import sqlalchemy.pool as pool
import traceback
from util import retrieve_db_info, AuthError, FASError

import gettext
t = gettext.translation('python-fedora', '/usr/share/locale')
_ = t.ugettext

psycopg2 = pool.manage(psycopg2, pool_size=5, max_overflow=15)

# When we encrypt the passwords in the database change to this:
# encrypt_password = lambda pw: sha.new(pw).hexdigest()
encrypt_password = lambda pw: pw

# Name of the database
dbName = 'fedorausers'
# Due to having live and test auth db's setup in the config file, we have to
# use 'live' rather than 'auth' as the key.
dbAlias = 'live'

class DBError(FASError):
    pass

class AccountSystem(object):
    '''Fedora Account System.

    This object provides an interface to the account system.  It allows you
    to connect to it for authentication, information retrieval, and etc.
    '''

    def __init__(self, user=None, password=None):
        '''Initialize the Account System.
       
        Arguments:
        :user: Can either be a string containing the username or an integer
          containing the user.id that we are verifying the password for.
        :password: Is a string containing the unencrypted password.

        Exceptions:
        :AuthError: Returned if we were unable to get config information
          from the database or the user-password combination failed.
        '''

        try:
            dbInfo = retrieve_db_info(dbAlias)
        except IOError:
            raise AuthError, _('Authentication config fedora-db-access is' \
                    ' not available')

        # Load the database information into internal values
        self.dbName = dbName
        self.dbHost = dbInfo['host']
        self.dbUser = dbInfo['user']
        # Some db connections have no password
        self.dbPass = dbInfo.get('password')

        # Set the user that is accessing the account system.
        if user and password:
            self.change_user(user, password)
        else:
            self.userId = None

        # Preseed a list of FAS accounts with bugzilla addresses
        # This allows us to specify a different email for bugzilla than is
        # in the FAS db.  It is a hack, however, until FAS has a field for the
        # bugzilla address.
        self.__bugzilla_email = {
                # Konstantin Ryabitsev: mricon@gmail.com
                100029: 'icon@fedoraproject.org',
                # Sean Reifschneider: jafo@tummy.com
                100488: 'jafo-redhat@tummy.com',
                # Karen Pease: karen-pease@uiowa.edu
                100281: 'meme@daughtersoftiresias.org',
                # Robert Scheck: redhat@linuxnetz.de
                100093: 'redhat-bugzilla@linuxnetz.de',
                # Scott Bakers: bakers@web-ster.com
                100881: 'scott@perturb.org',
                # Colin Charles: byte@aeon.com.my
                100014: 'byte@fedoraproject.org',
                # W. Michael Petullo: mike@flyn.org
                100136: 'redhat@flyn.org',
                # Elliot Lee: sopwith+fedora@gmail.com
                100060: 'sopwith@redhat.com',
                # Control Center Team: Bugzilla user but email doesn't exist
                9908: 'control-center-maint@redhat.com',
                }
        # A few people have an email account that is used in owners.list but
        # have setup a bugzilla account for their primary account system email
        # address now.  Map these here.
        self.__alternate_email = {
                # Damien Durand: splinux25@gmail.com
                'splinux@fedoraproject.org': 100406,
                # Kevin Fenzi: kevin@tummy.com
                'kevin-redhat-bugzilla@tummy.com': 100037,
                }
        for bugzillaMap in self.__bugzilla_email.items():
            self.__alternate_email[bugzillaMap[1]] = bugzillaMap[0]

        # We use the two mappings as follows::
        # When looking up a user by email, use __alternate_email.
        # When looking up a bugzilla email address use __bugzilla_email.
        #
        # This allows us to parse in owners.list and have a value for all the
        # emails in there while not using the alternate email unless it is
        # the only option.

    def _raise_dberror(self):
        '''Clear the connection pool and raise an error.

        When a db error occurs, we want to clear the connection pool so there's
        no stale connections to fail at a later date.  Also rethrow the
        exception as a DBError so calling code doesn't need to worry about
        what database is being used to store the fas info.
        '''
        # Clear the connections since they are probably targetting a closed
        # connection.
        psycopg2.dispose(database=self.dbName, host=self.dbHost,
                user=self.dbUser, password=self.dbPass)

        # Raise the exception as an AuthError as calling code doesn't need to
        # deal with which db was used.
        raise DBError(traceback.format_exc())

    def get_dbCmd(self):
        '''Return an isolated db cursor to use for the query.

        Some notes:
        Since we are using sqlalchemy.pool to manage psycopg2,
        it's pretty efficient to create a new connection for every query.

        We return a new query eveytime so that different methods won't
        interfere with each other.  (For instance, if one has to rollback while
        a separate thread has data it hasn't committed yet.)

        Defining this as a property so referencing self.dbCmd will retrieve a
        new database cursor as if it was an attribute.
        '''
        # Open a connection to the database
        db = psycopg2.connect(database=self.dbName, host=self.dbHost,
                user=self.dbUser, password=self.dbPass)
        return db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    dbCmd = property(get_dbCmd)

    def verify_user_pass(self, user, password):
        '''Verify that the username-password combination are valid.
        
        Arguments:
        :user: Can either be a string containing the username or an integer
          containing the user.id that we are verifying the password for.
        :password: Is a string containing the unencrypted password.

        Returns: True if the user and password match.  Otherwise, False.

        Exceptions:
        :AuthError: Returned if the user does not exist.
        '''
        cursor = self.dbCmd
        if isinstance(user, int):
            condition = ' id ='
        else:
            condition = ' username ='
        try:
            cursor.execute('select id, password from person where'
                + condition + ' %(user)s', {'user' : user})
            person = cursor.fetchone()
        except psycopg2.DatabaseError, e:
            self._raise_dberror()

        if not person:
            raise AuthError, 'No such user: %s' % user

        if person['id'] < 10000 or person['password'] == '':
            # This is a system user account or the password is blank (disabled)
            # Don't allow this user to login.
            return False

        if person['password'] == encrypt_password(password):
            return True
        else:
            return False

    def change_user(self, user, password):
        '''Set the AccountSystem to act on behalf of a user.
        
        Arguments:
        :user: Can either be a string containing the username or an integer
          containing the user.id that we are verifying the password for.
        :password: Is a string containing the unencrypted password.

        Exceptions:
        :AuthError: If the username and password don't match or the user
          doesn't exist.
        '''
        # Authenticate the user
        if self.verify_user_pass(user, password):
            # User has authenticated, set them as the current AccountSystem user
            if isinstance(user, int):
                self.userid = user
            else:
                self.userid = self.get_user_id(user)
        else:
            raise AuthError, _('Username/password mismatch for %(username)s') \
                    % {'username': user}

    def get_user_id(self, username):
        '''Retrieve the userid from a username.

        Arguments:
        :username: The username to lookup.

        Exceptions:
        :AuthError: The user does not exist.
        '''
        cursor = self.dbCmd
        try:
            cursor.execute('select id from person'
                ' where username = %(username)s', {'username' : username})
            result = cursor.fetchone()
        except psycopg2.DatabaseError, e:
            self._raise_dberror()
        if result:
            return result[0]
        else:
            raise AuthError, _('No such user: %(username)s') \
                    % {'username': username}

    def get_user_id_from_email(self, email):
        '''Retrieve a userid from an email address.

        Arguments:
        :email: The email address to lookup.
        
        Exceptions:
        :AuthError: The user does not exist.

        Returns: The userid to which the email belongs.
        '''
        cursor = self.dbCmd
        try:
            cursor.execute('select id from person'
                ' where email = %(email)s', {'email' : email})
            result = cursor.fetchone()
        except psycopg2.DatabaseError, e:
            self._raise_dberror()
        if result:
            return result[0]
        else:
            # Try running it through our list of oddball emails:
            if email in self.__alternate_email:
                return self.__alternate_email[email]
            raise AuthError, _('No such user: %(username)s') \
                    % {'username': username}

    def get_users(self, keyField=None):
        '''Retrieve most commonly needed data about all users.

        This allows us to make one query of the database instead of multiple
        when generating things like acl lists for cvs.

        Arguments:
          :keyField: the field from the database that we should key on for the
            dict.  Valid keyFields are: 'id', 'email', 'bugzilla_email', or
            'username'.

        Returns: a dict keyed on keyField.  Each dict record contains a dict
        with the following entries:
          :id: User id in the account system
          :username: The public username
          :email: Email address
          :bugzilla_email: Email address used in bugzilla
          :human_name: The user's common name
        '''
        # assure ourselves of having a valid key for the dict
        fields = ('id', 'email', 'bugzilla_email', 'username')
        if keyField not in fields:
            keyField = 'id'
        
        # Fetch the users from the database
        cursor = self.dbCmd
        try:
            cursor.execute("select '' as bugzilla_email, id, username,"
                " email, human_name"
                " from person")
        except psycopg2.DatabaseError, e:
            self._raise_dberror()

        people = {}
        # Add the users to a dict
        for person in cursor.fetchall():
            # Fill the bugzilla_email field.
            # NOTE:  Because of a bug in the psycopg2 DictCursor, you have
            # to use list notation to set values even though you can use
            # dict keys to retrieve them.
            person[0] = self.__bugzilla_email.get(person['id'],
                    person['email'])
            people[person[keyField]] = person

        return people

    def get_user_info(self, user=None):
        ### FIXME: Check the information we return against the FAS2 schema.
        # Make sure the data we're returning has a field there that's easy to
        # map.  Consider translating to the FAS2 names instead of returning a
        # raw dictCursor.
        '''Retrieve information for user.
        
        Returns the subset of information about user that the currently
        authenticated user is allowed to see.

        If the authenticated user is None: Only return information suitable
        for the general public:
          :id: User id in the account system
          :username: The public username
          :email: Email address
          :bugzilla_email: Email address used in bugzilla
          :human_name: The user's common name
          :gpg_keyid: The gpg id of the user
          :comments: Public comments from the user
          :affiliation: What group the user is a part of
          :creation: Date the user was created
          :ircnick: The user's irc nickname
          Group Information: The following information about the groups the user
          has been approved into.  (Will not list groups for which the user is
          not approved.)
            :id: group id
            :name: group name
            :role_type: the user's role in the group
            :creation: when the user was added to the group

        If an authenticated user is requesting the information, you get this
        additional information:
          :ssh_key: Ssh public key
          :postal_address: Mailing address
          :telephone: Telephone number
          :facsimile: FAX number
          :approval_status:
          :wiki_prefs:
          And additional group information including groups for which the user's
          membership is pending.
            :owner_id: Owner of the group
            :needs_sponsor: Whether the group requires a sponsor to add a user
            :user_can_remove: Whether the user is allowed to remove themselves
            :role_status: Whether the user is approved yet

        If the authenticated user of the AccountSystem is retrieving information
        about their own account, they get this in addition:
          :password: The user's password

        If the authenticated user is the accounts admin, then they have access
        to all of the above plus:
          :internal_comments: Comments the admin has made about the user
          Group information:
            :internal_comments: Comments left by a group admin about the user's
              involvement with this group.

        Arguments:
        :user: Can either be a string containing the username or an integer
          containing the user.id to lookup information for.  If this is None,
          return information about the currently authenticated user.

        Returns: A tuple of (UserData, GroupData) that is associated with
          the user.  UserData is a dict of information about the user.
          GroupData is a tuple of dicts holding group information.
        '''
        if not user:
            if not self.userId:
                raise AuthError, _('No user set')
            user = self.userId

        if not isinstance(user, int):
            user = self.get_user_id(user)

        userDict = {'user' : user}

        cursor = self.dbCmd
        if not self.userId:
            # Retrieve publically viewable information
            try:
                cursor.execute("select '' as bugzilla_email, id, username,"
                    " email, human_name, gpg_keyid, comments, affiliation,"
                    " creation, ircnick"
                    " from person where id = %(user)s",
                    userDict)
                person = cursor.fetchone()
                cursor.execute("select g.id, g.name, r.role_type, r.creation"
                    " from project_group as g, person as p, role as r"
                    " where g.id = r.project_group_id and p.id = r.person_id"
                    " and r.role_status = 'approved' and p.id = %(user)s",
                    userDict)
            except psycopg2.DatabaseError, e:
                self._raise_dberror()

        else:
            if user == self.userId:
                # The request is from the user for information about himself,
                # retrieve everything except internal_comments
                try:
                    cursor.execute("select '' as bugzilla_email, id, username,"
                        " email, human_name, gpg_keyid, comments, affiliation,"
                        " creation, ircnick, approval_status, wiki_prefs,"
                        " ssh_key, postal_address, telephone, facsimile,"
                        " password"
                        " where id = %(user)s",
                        userDict)
                    person = cursor.fetchone()
                    cursor.execute("select g.id, g.name, r.role_type,"
                        " r.creation, g.owner_id, g.needs_sponsor,"
                        " g.user_can_remove, r.role_status"
                        " from project_group as g, person as p, role as r"
                        " where g.id = r.project_group_id"
                        " and p.id = r.person_id and p.id = %(user)s",
                        userDict)
                except psycopg2.DatabaseError, e:
                    self._raise_dberror()

            elif self.userId == adminUserId:
                # Admin can view everything
                try:
                    cursor.execute("select '' as bugzilla_email, id, username,"
                        " email, human_name, gpg_keyid, comments, affiliation,"
                        " creation, ircnick, approval_status, wiki_prefs,"
                        " ssh_key, postal_address, telephone, facsimile,"
                        " password, internal_comments"
                        " where id = %(user)s",
                        userDict)
                    person = cursor.fetchone()
                    cursor.execute("select g.id, g.name, r.role_type,"
                            " r.creation, g.owner_id, g.needs_sponsor,"
                            " g.user_can_remove, r.role_status,"
                            " r.internal_comments"
                            " from project_group as g, person as p, role as r"
                            " where g.id = r.project_group_id"
                            " and p.id = r.person_id"
                            " and p.id = %(user)s",
                            userDict)
                except psycopg2.DatabaseError, e:
                    self._raise_dberror()
            else:
                # Retrieve everything but password and internal_comments for
                # another user in the account system
                try:
                    cursor.execute("select '' as bugzilla_email, id, username,"
                        " email, human_name, gpg_keyid, comments, affiliation,"
                        " creation, ircnick, approval_status, wiki_prefs,"
                        " ssh_key, postal_address, telephone, facsimile,"
                        " password, internal_comments"
                        " where id = %(user)s",
                        userDict)
                    person = cursor.fetchone()
                    cursor.execute("select g.id, g.name, r.role_type,"
                        " r.creation, g.owner_id, g.needs_sponsor,"
                        " g.user_can_remove, r.role_status"
                        " from project_group as g, person as p, role as r"
                        " where g.id = r.project_group_id"
                        " and p.id = r.person_id and p.id = %(user)s",
                        userDict)
                except psycopg2.DatabaseError, e:
                    self._raise_dberror()
        try:
            groups = cursor.fetchall()
        except psycopg2.DatabaseError, e:
            self._raise_dberror()

        # We couldn't find any records for this person
        if not person:
            raise AuthError, _('No such user %(user)s') % userDict

        # Fill the bugzilla_email field.
        # NOTE:  Because of a bug in the psycopg2 DictCursor, you have to use
        # list notation to set values even though you can use dict keys to
        # retrieve them.
        person[0] = self.__bugzilla_email.get(user, person['email'])
        for fieldNum in range(0, len(person) - 1):
            if isinstance(person[fieldNum], str):
                person[fieldNum] = person[fieldNum].decode('utf-8')
        return (person, groups)

    def get_group_info(self, group):
        '''Retrieve information about the group.
        '''
        cursor = self.dbCmd
        try:
            cursor.execute("select * from project_group where id = %(group)s",
                    dict(group=group))
            result = cursor.fetchone()
        except psycopg2.databaseerror, e:
            self._raise_dberror()
        if result:
            for fieldNum in range(0, len(result) - 1):
                if isinstance(result[fieldNum], str):
                    result[fieldNum] = result[fieldNum].decode('utf-8')
            return result
        else:
            raise AuthError, _('No such group: %(group)s') % {'group': group}

    def modify_user(self, user):
        '''Change information for user. (Admin or owner)

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def modify_group(self, group):
        '''Change information for a group. (Admin, owner)

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def change_user_pass(self, oldpassword, newpassword, user=None):
        '''Change user's password.

        Function to change a user's password.
        
        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def request_group(self, user, group, level):
        '''Request that user be added to group at level.

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def approve_group(self, user, group, level):
        '''Approve a user for a group (Admin, groupowner)

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def add_user(self, user, userInfo):
        '''Add a new user. (anyone)

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def add_group(self, group):
        '''Add a new group. (Admin)

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def remove_user(self, user):
        '''(Admin or owner)

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass

    def remove_group(self, group):
        '''(Admin)

        (Not Yet Implemented)
        '''
        raise NotImplementedError
        pass
