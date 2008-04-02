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
from fedora.tg.client import BaseClient, AuthError, ServerError

class FASError(Exception):
    '''FAS Error'''
    pass

class CLAError(FASError):
    '''CLA Error'''
    pass

class AccountSystem(BaseClient):

    def __init__(self, baseURL, username=None, password=None, debug=False):
        super(AccountSystem, self).__init__(baseURL=baseURL, username=username, password=password, debug=debug)

    # TODO: Use exceptions properly
    def group_by_id(self, id):
        """Returns a group object based on its id"""
        params = {'id': id}
        request = self.send_request('json/group_by_id', auth=True, input=params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def person_by_id(self, id):
        """Returns a person object based on its id"""
        params = {'id': id}
        request = self.send_request('json/person_by_id', auth=True, input=params)
        if request['success']:
            return request['person']
        else:
            return dict()

    def group_by_name(self, groupname):
        """Returns a group object based on its name"""
        params = {'groupname': groupname}
        request = self.send_request('json/group_by_name', auth=True, input=params)
        if request['success']:
            return request['group']
        else:
            return dict()

    def person_by_username(self, username):
        """Returns a person object based on its username"""
        params = {'username': username}
        request = self.send_request('json/person_by_username', auth=True, input=params)
        if request['success']:
            return request['person']
        else:
            return dict()

    def user_id(self):
        """Returns a dict relating user IDs to usernames"""
        request = self.send_request('json/user_id', auth=True)
        return request['people']

    def user_gencert(self):
        """Generate a cert for a user"""
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
