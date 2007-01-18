# A TurboGears interface to the Fedora Account System

import sys
sys.path.extend(['/home/devel/sopwith/cvs/fedora-config/fedora-accounts'])
import website

import cherrypy
import sha
import md5
import random
from turbogears.jsonify import *
from sqlobject import *
from sqlobject.inheritance import InheritableSQLObject
from datetime import *

import logging
log = logging.getLogger("turbogears.identity")

from turbogears import identity
from turbogears.database import PackageHub

from turbogears.identity.soprovider import TG_VisitIdentity

hub = PackageHub("turbogears.identity")
__connection__ = hub

authdbh = website.get_dbh('auth', dbctx='live')

try:
    set, frozenset
except NameError:
    from sets import Set as set, ImmutableSet as frozenset

class FedoraUser:
    def __init__(self, userinfo):
        self.__dict__ = userinfo

    def __getattr__(self, nom):
        if nom == 'displayName':
            return self.human_name
        raise AttributeError, "Attribute not found"

class FedoraAccountSystemIdentity(object):
    def __init__(self, visit_id, user=None):
        if user:
            self._user= user
        self.visit_id= visit_id
    
    def _get_user(self):
        try:
            return self._user
        except AttributeError:
            # User hasn't already been set
            pass
        # Attempt to load the user. After this code executes, there *WILL* be
        # a _user attribute, even if the value is None.
        try:
            visit= TG_VisitIdentity.by_visit_id( self.visit_id )
        except SQLObjectNotFound:
            # The visit ID is invalid
            self._user= None
            return None
        userinfo = website.get_user_info(authdbh, visit.user_id)
        if userinfo:
            self._user = FedoraUser(userinfo)
            return self._user
        else:
            log.warning( "No such user with ID: %s", visit.user_id )
            self._user= None
            return None
    user= property(_get_user)
    
    def _get_user_name(self):
        if not self.user:
            return None
        return self.user.get('username', 'anonymous')
    user_name= property(_get_user_name)

    def _get_anonymous(self):
        return self.user is None
    anonymous = property(_get_anonymous)
    
    def _get_permissions(self):
        try:
            return self._permissions
        except AttributeError:
            # Permissions haven't been computed yet
            pass
        self._permissions= frozenset()
        return self._permissions
    permissions = property(_get_permissions)
    
    def _get_groups(self):
        try:
            return self._groups
        except AttributeError:
            # Groups haven't been computed yet
            pass
        if not self.user:
            self._groups= frozenset()
        else:
            self._groups= frozenset([g[0] for g in website.get_user_groups(authdbh, self.user.id)])
        return self._groups
    groups = property(_get_groups)

    def logout(self):
        '''
        Remove the link between this identity and the visit.
        '''
        if not self.visit_id:
            return
        try:
            visit= TG_VisitIdentity.by_visit_id(self.visit_id)
            visit.destroySelf()
            # Clear the current identity
            anon = FedoraAccountSystemIdentity(None, None)
            anon.anonymous= True
            identity.set_current_identity( anon )
        except:
            pass

class FedoraAccountSystemIdentityProvider(object):
    def __init__(self):
        super(FedoraAccountSystemIdentityProvider, self).__init__()
        get=cherrypy.config.get
        
        # Default encryption algorithm is to use plain text passwords
        algorithm= get( "identity.soprovider.encryption_algorithm", None )
        if "md5"==algorithm:
            self.encrypt_password= lambda pw: md5.new(pw).hexdigest()
        elif "sha1"==algorithm:
            self.encrypt_password= lambda pw: sha.new(pw).hexdigest()
        else:
            self.encrypt_password= lambda pw: pw

    def create_provider_model( self ):
        # create the database tables
        try:
            hub.begin()
            TG_VisitIdentity.createTable(ifNotExists=True)
            hub.commit()
        except KeyError:
            log.warning( "No database is configured: FedoraAccountSystemIdentityProvider is disabled." )
            return

    def validate_identity( self, user_name, password, visit_id ):
        '''
        Look up the identity represented by user_name and determine whether the
        password is correct.
        
        Must return either None if the credentials weren't valid or a tuple
        containing the following information:
            user_name: original user_name
            user: a provider dependant user object
            groups: set of group IDs
            permissions: set of permission IDs
        '''
        try:
            userinfo = website.do_checkpass_full(authdbh, user_name, password)
            if not userinfo:
                log.info( "Passwords don't match for user: %s", user_name )
                return
            
            # Link the user to the visit
            try:
                link= TG_VisitIdentity.by_visit_id( visit_id )
                link.user_id= userinfo['id']
            except SQLObjectNotFound:
                link = TG_VisitIdentity( visit_id=visit_id, user_id=userinfo['id'])
            return FedoraAccountSystemIdentity( visit_id, FedoraUser(userinfo) )
            
        except SQLObjectNotFound:
            log.warning( "No such user: %s", user_name )
            return None

    def load_identity( self, visit_id ):
        '''
        Lookup the principal represented by user_name. Return None if there is no
        principal for the given user ID.
        
        Must return a dictionary with keys:
            user_name: original userID
            user: a provider dependant user object
            groups: set of group IDs
            permissions: set of permission IDs
        '''
        return FedoraAccountSystemIdentity( visit_id )
    
    def anonymous_identity( self ):
        '''
        Return a dictionary with the following keys:
            user_name: the ID of the anonymous user
            user: a provider specific user object
            groups: set of group IDs to which anonymous users belong
            permissions: set of permission IDs granted to anonymous users
        '''
        return FedoraAccountSystemIdentity( None )
