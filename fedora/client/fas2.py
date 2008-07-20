# -*- coding: utf-8 -*-
#
# Copyright © 2008  Ricky Zhou, Red Hat, Inc. All rights reserved.
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
# Author(s): Ricky Zhou <ricky@fedoraproject.org>
#            Toshio Kuratomi <tkuratom@redhat.com>
#
'''
Provide a client module for talking to the Fedora Account System.
'''
import urllib

from fedora.client import DictContainer, BaseClient, ProxyClient, \
        AuthError, AppError, FedoraServiceError, FedoraClientError
from fedora import __version__

### FIXME: To merge:
# /usr/bin/fasClient from fas
# API from Will Woods
# API from MyFedora

class FASError(FedoraClientError):
    '''FAS Error'''
    pass

class CLAError(FASError):
    '''CLA Error'''
    pass

class AccountSystem(BaseClient):
    '''An object for querying the Fedora Account System.

    The Account System object provides a python API for talking to the Fedora
    Account System.  It abstracts the http requests, cookie handling, and
    other details so you can concentrate on the methods that are important to
    your program.
    '''
    proxy = None
    def __init__(self, base_url='https://admin.fedoraproject.org/accounts/',
            *args, **kwargs):
        '''Create the AccountSystem client object.

        Keyword Arguments:
        :base_url: Base of every URL used to contact the server.  Defalts to
            the Fedora PackageDB instance.
        :useragent: useragent string to use.  If not given, default to
            "Fedora BaseClient/VERSION"
        :debug: If True, log debug information
        :username: username for establishing authenticated connections
        :password: password to use with authenticated connections
        :session_cookie: user's session_cookie to connect to the server
        :cache_session: if set to true, cache the user's session cookie on the
            filesystem between runs.
        '''
        if 'useragent' not in kwargs:
            kwargs['useragent'] = 'Fedora Account System Client/%s' \
                    % __version__
        super(AccountSystem, self).__init__(base_url, *args, **kwargs)
        # We need a single proxy for the class to verify username/passwords
        # against.
        if not self.proxy:
            self.proxy = ProxyClient(base_url, self.useragent, self.debug)

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
                # Máirín Duffy
                100548: 'duffy@redhat.com',
                # Muray McAllister: murray.mcallister@gmail.com
                102321: 'mmcallis@redhat.com',
                # William Jon McCann: mccann@jhu.edu
                102489: 'jmccann@redhat.com',
                # Matt Domsch's rebuild script -- bz email goes to /dev/null
                103590: 'ftbfs@fedoraproject.org',
                # Sindre Pedersen Bjørdal: foolish@guezz.net
                100460 : 'sindrepb@fedoraproject.org',
                # Jesus M. Rodriguez: jmrodri@gmail.com
                102180: 'jesusr@redhat.com',
                # Jeff Sheltren: jeff@osuosl.org
                100058: 'sheltren@fedoraproject.org',
                # Roozbeh Pournader: roozbeh@farsiweb.info
                100350: 'roozbeh@gmail.com',
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
        for bugzilla_map in self.__bugzilla_email.items():
            self.__alternate_email[bugzilla_map[1]] = bugzilla_map[0]

        # We use the two mappings as follows::
        # When looking up a user by email, use __alternate_email.
        # When looking up a bugzilla email address use __bugzilla_email.
        #
        # This allows us to parse in owners.list and have a value for all the
        # emails in there while not using the alternate email unless it is
        # the only option.

    # TODO: Use exceptions properly

    ### Groups ###

    def group_by_id(self, group_id):
        '''Returns a group object based on its id'''
        params = {'id': int(group_id)}
        request = self.send_request('json/group_by_id', auth = True,
                req_params = params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def group_by_name(self, groupname):
        '''Returns a group object based on its name'''
        params = {'groupname': groupname}
        request = self.send_request('json/group_by_name', auth = True,
                req_params = params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def group_members(self, groupname):
        '''Return a list of people approved for a group.

        This method returns a list of people who are in the requested group.
        The people are all approved in the group.  Unapproved people are not
        shown.  The format of data is::

        [{'username': 'person1', 'role_type': 'user'},
        {'username': 'person2', 'role_type': 'sponsor'}]

        role_type can be one of 'user', 'sponsor', or 'administrator'.
        '''
        request = self.send_request('/group/dump/%s' %
                urllib.quote(groupname), auth=True)

        return [DictContainer(username=user[0], role_type=user[3])
                    for user in request['people']]

    ### People ###

    def person_by_id(self, person_id):
        '''Returns a person object based on its id'''
        person_id = int(person_id)
        params = {'id': person_id}
        request = self.send_request('json/person_by_id', auth=True,
                req_params=params)

        if request['success']:
            if person_id in self.__bugzilla_email:
                request['person']['bugzilla_email'] = \
                        self.__bugzilla_email[person_id]
            else:
                request['person']['bugzilla_email'] = request['person']['email']
            return request['person']
        else:
            return dict()

    def person_by_username(self, username):
        '''Returns a person object based on its username'''
        params = {'username': username}
        request = self.send_request('json/person_by_username', auth = True,
                req_params = params)
        person = request['person']
        if request['success']:
            if person['id'] in self.__bugzilla_email:
                person['bugzilla_email'] = self.__bugzilla_email[person['id']]
            else:
                person['bugzilla_email'] = person['email']
            return person
        else:
            return dict()

    def user_id(self):
        '''Returns a dict relating user IDs to usernames'''
        request = self.send_request('json/user_id', auth=True)
        people = {}
        for person_id, username in request['people'].items():
            # change userids from string back to integer
            people[int(person_id)] = username
        return people

    def people_by_id(self):
        '''
        Returns a dict relating user IDs to human_name, email, username,
        and bugzilla email
        '''
        ### FIXME: This should be implemented on the server as a single call
        request = self.send_request('/json/user_id', auth=True)
        user_to_id = {}
        people = DictContainer()
        for person_id, username in request['people'].items():
            person_id = int(person_id)
            # change userids from string back to integer
            people[person_id] = {'username': username, 'id': person_id}
            user_to_id[username] = person_id

        # Retrieve further useful information about the users
        request = self.send_request('/group/dump', auth=True)
        for user in request['people']:
            userid = user_to_id[user[0]]
            person = people[userid]
            person['email'] = user[1]
            person['human_name'] = user[2]
            if userid in self.__bugzilla_email:
                person['bugzilla_email'] = self.__bugzilla_email[userid]
            else:
                person['bugzilla_email'] = person['email']

        return people

    ### Configs ###

    def get_config(self, username, application, attribute):
        '''Return the config entry for the key values.

        Arguments:
        :username: Username of the person
        :application: Application for which the config is set
        :attribute: Attribute key to lookup

        Returns: The unicode string that describes the value.  If no entry
            matched the username, application, and attribute then None is
            returned.
        '''
        request = self.send_request('config/list/%s/%s/%s' %
                (username, application, attribute), auth=True)
        if 'exc' in request:
            raise AppError(name = request['exc'], message = request['tg_flash'])

        # Return the value if it exists, else None.
        if 'configs' in request and attribute in request['configs']:
            return request['configs'][attribute]
        return None

    def get_configs_like(self, username, application, pattern=u'*'):
        '''Return the config entries that match the keys and the pattern.

        Note: authentication on the server will prevent anyone but the user
        or a fas admin from viewing or changing their configs.

        Arguments:
        :username: Username of the person
        :application: Application for which the config is set
        :pattern: A pattern to select values for.  This accepts * as a
            wildcard character. Default='*'

        Returns:
        A dict mapping ``attribute`` to ``value``.
        '''
        request = self.send_request('config/list/%s/%s/%s' %
                (username, application, pattern), auth=True)
        if 'exc' in request:
            raise AppError(name = request['exc'], message = request['tg_flash'])

        return request['configs']

    def set_config(self, username, application, attribute, value):
        '''Set a config entry in FAS for the user.

        Note: authentication on the server will prevent anyone but the user
        or a fas admin from viewing or changing their configs.

        Arguments:
        :username: Username of the person
        :application: Application for which the config is set
        :attribute: The name of the config key that we're setting
        :value: The value to set this to
        '''
        request = self.send_request('config/set/%s/%s/%s' %
                (username, application, attribute),
                req_params={'value': value}, auth=True)

        if 'exc' in request:
            raise AppError(name = request['exc'], message = request['tg_flash'])

    ### Certs ###

    def user_gencert(self):
        '''Generate a cert for a user'''
        try:
            request = self.send_request('user/gencert', auth=True)
        except FedoraServiceError:
            raise
        if not request['cla']:
            raise CLAError
        return "%(cert)s\n%(key)s" % request

    ### Passwords ###

    def verify_password(self, username, password):
        '''Return whether the username and password pair are valid.

        Arguments:
        :username: username to try authenticating
        :password: password for the user

        Returns: True if the username/password are valid.  False otherwise.
        '''
        try:
            # This will attempt to authenticate to the account system and
            # raise an AuthError if the password and username don't match. 
            self.proxy.send_request('/',
                    auth_params={'username': username, 'password': password})
        except AuthError:
            return False
        except:
            raise
        return True
