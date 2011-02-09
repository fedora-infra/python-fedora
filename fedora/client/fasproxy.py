# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2009  Red Hat, Inc.
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
'''Implement a class that sets up threadsafe communication with the Fedora
   Account System

.. moduleauthor:: Ricky Zhou <ricky@fedoraproject.org>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>

.. versionadded:: 0.3.17
'''

from fedora.client import AuthError, AppError
from fedora.client.proxyclient import ProxyClient
from fedora import __version__, b_

import logging
log = logging.getLogger(__name__)

class FasProxyClient(ProxyClient):
    '''A threadsafe client to the Fedora Account System.'''

    def __init__(self, base_url='https://admin.fedoraproject.org/accounts/',
            *args, **kwargs):
        '''A threadsafe client to the Fedora Account System.

        This class is optimized to proxy multiple users to the account system.
        ProxyClient is designed to be threadsafe so that code can instantiate
        one instance of the class and use it for multiple requests for
        different users from different threads.

        If you want something that can manage a single user's connection to
        the Account System then use fedora.client.AccountSystem instead.

        :kwargs base_url: Base of every URL used to contact the server.
            Defaults to the Fedora Project FAS instance.
        :kwargs useragent: useragent string to use.  If not given, default to
            "FAS Proxy Client/VERSION"
        :kwarg session_name: name of the cookie to use with session handling
        :kwarg debug: If True, log debug information
        :kwarg insecure: If True, do not check server certificates against
            their CA's.  This means that man-in-the-middle attacks are
            possible against the `BaseClient`. You might turn this option on
            for testing against a local version of a server with a self-signed
            certificate but it should be off in production.
        '''
        if 'useragent' not in kwargs:
            kwargs['useragent'] = 'FAS Proxy Client/%s' % __version__
        if 'session_as_cookie' in kwargs and kwargs['session_as_cookie']:
            # No need to allow this in FasProxyClient as it's deprecated in
            # ProxyClient
            raise TypeError(b_('FasProxyClient() got an unexpected keyword'
                ' argument \'session_as_cookie\''))
        kwargs['session_as_cookie'] = False
        super(FasProxyClient, self).__init__(base_url, *args, **kwargs)

    def login(self, username, password):
        '''Login to the Account System

        :arg username: username to send to FAS
        :arg password: Password to verify the username with
        :returns" the session id FAS has associated with the user
        :raises AuthError: if the username and password do not work
        '''
        return self.send_request('/login',
                auth_params={'username': username, 'password':password})

    def logout(self, session_id):
        '''Logout of the Account System

        :arg session_id: a FAS session_id to remove from FAS
        '''
        self.send_request('/logout', auth_params={'session_id': session_id})

    def refresh_session(self, session_id):
        '''Try to refresh a session_id to prevent it from timing out

        :arg session_id: FAS session_id to refresh
        :returns: session_id that FAS has set now
        '''
        return self.send_request('', auth_params={'session_id': session_id})

    def verify_session(self, session_id):
        '''Verify that a session is active.

        :arg session_id: session_id to verify is currently associated with a logged in user
        :returns: True if the session_id is valid.  False otherwise.
        '''
        try:
            self.send_request('/home', auth_params={'session_id': session_id})
        except AuthError:
            return False
        except:
            raise
        return True

    def verify_password(self, username, password):
        '''Return whether the username and password pair are valid.

        :arg username: username to try authenticating
        :arg password: password for the user
        :returns: True if the username/password are valid.  False otherwise.
        '''
        try:
            self.send_request('/home', auth_params={'username': username,
                'password': password})
        except AuthError:
            return False
        except:
            raise
        return True

    def get_user_info(self, auth_params):
        '''Retrieve information about a logged in user.

        :arg auth_params: Auth information for a particular user.  For
            instance, this can be a username/password pair or a session_id.
            Refer to
            :meth:`fedora.client.proxyclient.ProxyClient.send_request` for all
            the legal values for this.
        :returns: a tuple of session_id and information about the user.
        :raises AuthError: if the auth_params do not give access
        '''
        request = self.send_request('/user/view', auth_params=auth_params)
        return (request[0], request[1]['person'])

    def person_by_id(self, person_id, auth_params):
        '''Retrieve information about a particular person

        :arg auth_params: Auth information for a particular user.  For
            instance, this can be a username/password pair or a session_id.
            Refer to
            :meth:`fedora.client.proxyclient.ProxyClient.send_request` for all
            the legal values for this.
        :returns: a tuple of session_id and information about the user.
        :raises AppError: if the server returns an exception
        :raises AuthError: if the auth_params do not give access
        '''
        request = self.send_request('/json/person_by_id',
                req_params={'person_id': person_id}, auth_params=auth_params)
        if request[1]['success']:
            # In a devel version of FAS, membership info was returned separately
            # This has been corrected in a later version
            # Can remove this code at some point
            if 'approved' in request[1]:
                request[1]['person']['approved_memberships'] = \
                        request[1]['approved']
            if 'unapproved' in request[1]:
                request[1]['person']['unapproved_memberships'] = \
                        request[1]['unapproved']
            return (request[0], request[1]['person'])
        else:
            raise AppError(name='Generic AppError',
                    message=request[1]['tg_flash'])

    def group_list(self, auth_params):
        '''Retrieve a list of groups

        :arg auth_params: Auth information for a particular user.  For
            instance, this can be a username/password pair or a session_id.
            Refer to
            :meth:`fedora.client.proxyclient.ProxyClient.send_request` for all
            the legal values for this.
        :returns: a tuple of session_id and information about groups.  The
            groups information is in two fields:

            :groups: contains information about each group
            :memberships: contains information about which users are members
                of which groups
        :raises AuthError: if the auth_params do not give access
        '''
        request = self.send_request('/group/list', auth_params=auth_params)
        return request
