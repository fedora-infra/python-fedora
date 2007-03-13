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
'''
__version__='0.1'

adminUserId = 100001

import os
import psycopg2
import psycopg2.extras

# When we encrypt the passwords in the database change to this:
# encrypt_password = lambda pw: sha.new(pw).hexdigest()
encrypt_password = lambda pw: pw

# Name of the database
dbName = 'fedorausers'
# Due to having live and test auth db's setup in the config file, we have to
# use 'live' rather than 'auth' as the key.
dbAlias = 'live'

def retrieve_db_info(dbKey):
    '''Retrieve information to connect to the db from the filesystem.
    
    Arguments:
    :dbKey: The string identifying the database entry in the config file.

    Returns: A dictionary containing the values to use in connecting to the
      database.

    Exceptions:
    :IOError: Returned if the config file is not on the system.
    :AuthError: Returned if there is no record found for dbKey in the
      config file.
    '''
    # Open a filehandle to the config file
    if os.environ.has_key('HOME') and os.path.isfile(
            os.path.join(os.environ.get('HOME'), '.fedora-db-access')):
        fh = file(os.path.join(
            os.environ.get('HOME'), '.fedora-db-access'), 'r')
    elif os.path.isfile('/etc/sysconfig/fedora-db-access'):
        fh = file('/etc/sysconfig/fedora-db-access', 'r')
    else:
        raise IOError, 'fedora-db-access file does not exist.'

    # Read the file until we get the information for the requested db
    dbInfo = None
    for line in fh.readlines():
        if not line:
            break
        line = line.strip()
        if not line or line[0] == '#':
            continue
        pieces = line.split(None, 1)
        if len(pieces) < 2:
            continue
        if pieces[0] == dbKey:
            dbInfo = eval(pieces[1])
            break

    if fh:
        fh.close()
    if not dbInfo:
        raise AuthError, 'Authentication source "%s" not configured' % (dbName,)
    return dbInfo

class AuthError(Exception):
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
            raise AuthError, 'Authentication config fedora-db-access is' \
                    ' not available'
        # Some db connections have no password
        dbPass = dbInfo.get('password')

        # Open a connection to the db
        self.db = psycopg2.connect(database=dbName, host=dbInfo['host'],
                user=dbInfo['user'], password=dbPass)
        self.cursor = self.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Set the user that is accessing the account system.
        if user and password:
            self.change_user(user, password)
        else:
            self.userId = None

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
        if isinstance(user, int):
            condition = ' id ='
        else:
            condition = ' username ='
        self.cursor.execute('select id, password from person where'
            + condition + ' %(user)s', {'user' : user})
        person = self.cursor.fetchone()

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
            raise AuthError, 'Username/password mismatch for %s' % user

    def get_user_id(self, username):
        '''Retrieve the userid from a username.

        Arguments:
        :username: The username to lookup.

        Exceptions:
        :AuthError: The user does not exist.
        '''
        self.cursor.execute('select id from person'
            ' where username = %(username)s', {'username' : username})
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            raise AuthError, 'No such user: %s' % username

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
          :email: Email address
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
                raise AuthError, 'No user set'
            user = self.userId

        if not isinstance(user, int):
            user = self.get_user_id(user)

        userDict = {'user' : user}

        if not self.userId:
            # Retrieve publically viewable information
            self.cursor.execute('select id, username, human_name, gpg_keyid,'
                ' comments, affiliation, creation, ircnick'
                ' from person where id = %(user)s',
                userDict)
            person = self.cursor.fetchone()
            self.cursor.execute("select g.id, g.name, r.role_type, r.creation"
                " from project_group as g, person as p, role as r"
                " where g.id = r.project_group_id and p.id = r.person_id"
                " and r.role_status = 'approved' and p.id = %(user)s",
                userDict)

        else:
            if user == self.userId:
                # The request is from the user for information about himself,
                # retrieve everything except internal_comments
                self.cursor.execute("select id, username, email, human_name,"
                    " gpg_keyid, ssh_key, password, comments, postal_address,"
                    " telephone, facsimile, affiliation, creation,"
                    " approval_status, wiki_prefs, ircnick"
                    " where id = %(user)s",
                    userDict)
                person = self.cursor.fetchone()
                self.cursor.execute("select g.id, g.name, r.role_type,"
                    " r.creation, g.owner_id, g.needs_sponsor,"
                    " g.user_can_remove, r.role_status"
                    " from project_group as g, person as p, role as r"
                    " where g.id = r.project_group_id and p.id = r.person_id"
                    " and p.id = %(user)s",
                    userDict)
            elif self.userId == adminUserId:
                # Admin can view everything
                self.cursor.execute("select * from person where id = %(user)s",
                        userDict)
                person = self.cursor.fetchone()
                self.cursor.execute("select g.id, g.name, r.role_type,"
                        " r.creation, g.owner_id, g.needs_sponsor,"
                        " g.user_can_remove, r.role_status, r.internal_comments"
                        " from project_group as g, person as p, role as r"
                        " where g.id = r.project_group_id"
                        " and p.id = r.person_id"
                        " and p.id = %(user)s",
                        userDict)
            else:
                # Retrieve everything but password and internal_comments for
                # another user in the account system
                self.cursor.execute("select id, username, email, human_name,"
                    " gpg_keyid, ssh_key, comments, postal_address,"
                    " telephone, facsimile, affiliation, creation,"
                    " approval_status, wiki_prefs, ircnick"
                    " from person where id = %(user)s",
                    userDict)
                person = self.cursor.fetchone()
                self.cursor.execute("select g.id, g.name, r.role_type,"
                    " r.creation, g.owner_id, g.needs_sponsor,"
                    " g.user_can_remove, r.role_status"
                    " from project_group as g, person as p, role as r"
                    " where g.id = r.project_group_id and p.id = r.person_id"
                    " and p.id = %(user)s",
                    userDict)
        groups = self.cursor.fetchall()

        return (person, groups)

    def get_group_info(self, group):
        '''Retrieve information about the group.
        '''
        self.cursor.execute("select * from project-group where id = %(group)s",
                dict('group' : group))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            raise AuthError, 'No such group: %s' % group

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
