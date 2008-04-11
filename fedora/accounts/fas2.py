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
import urllib
import urllib2
import simplejson
from urlparse import urljoin
from fedora.client import BaseClient, AuthError, ServerError

class FASError(Exception):
    '''FAS Error'''
    pass

class CLAError(FASError):
    '''CLA Error'''
    pass

class AccountSystem(BaseClient):

    def __init__(self, baseURL, username=None, password=None, debug=False):
        super(AccountSystem, self).__init__(baseURL=baseURL, username=username, password=password, debug=debug)
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
                103590: ' ftbfs@fedoraproject.org',
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

    # TODO: Use exceptions properly
    def group_by_id(self, groupId):
        '''Returns a group object based on its id'''
        params = {'id': int(groupId)}
        request = self.send_request('json/group_by_id', auth=True, input=params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def person_by_id(self, personId):
        '''Returns a person object based on its id'''
        personId = int(personId)
        params = {'id': personId}
        request = self.send_request('json/person_by_id', auth=True,
                input=params)

        if request['success']:
            if personId in self.__bugzilla_email:
                request['person']['bugzilla_email'] = \
                        self.__bugzilla_email[personId]
            else:
                request['person']['bugzilla_email'] = request['person']['email']
            return request['person']
        else:
            return dict()

    def group_by_name(self, groupname):
        '''Returns a group object based on its name'''
        params = {'groupname': groupname}
        request = self.send_request('json/group_by_name', auth=True, input=params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def person_by_username(self, username):
        '''Returns a person object based on its username'''
        params = {'username': username}
        request = self.send_request('json/person_by_username', auth=True, input=params)
        if request['success']:
            if request['person']['id'] in self.__bugzilla_email:
                request['person']['bugzilla_email'] = \
                        self.__bugzilla_email[person['id']]
            else:
                request['person']['bugzilla_email'] = request['person']['email']
            return request['person']
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
        userToId = {}
        people = {}
        for person_id, username in request['people'].items():
            person_id = int(person_id)
            # change userids from string back to integer
            people[person_id] = {'username': username, 'id': person_id}
            userToId[username] = person_id

        # Retrieve further useful information about the users
        request = self.send_request('/group/dump', auth=True)
        for user in request['people']:
            username = userToId[user[0]]
            people[username]['email'] = user[1]
            people[username]['human_name'] = user[2]

        return people

    def user_gencert(self):
        '''Generate a cert for a user'''
        try:
            request = self.send_request('user/gencert', auth=True)
        except ServerError, e:
            raise
        if not request['cla']:
            raise CLAError
        return "%(cert)s\n%(key)s" % request

    def authenticate(self, username, password):
        """TODO"""
        req = urllib2.Request(urljoin(self.baseURL, 'login?tg_format=json'))
        req.add_data(urllib.urlencode({
            'user_name' : username,
            'password'  : password,
            'login'     : 'Login'
            }))
        try:
            response = urllib2.urlopen(req)
        except urllib2.HTTPError, e:
            if e.msg == 'Forbidden':
                return False
        jsonString = response.read()
        try:
            data = simplejson.loads(jsonString)
        except ValueError, e:
            # The response wasn't JSON data
            raise ServerError, str(e)
        try:
            if data['user']:
                return data['user']['username'] == username
        except KeyError:
            pass
        return False
