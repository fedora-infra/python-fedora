# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2012  Ricky Zhou, Red Hat, Inc.
# Copyright (c) 2015 Xavier Lamien
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
"""
Provide a client module for talking to the Fedora Account System.

.. moduleauthor:: Ricky Zhou <ricky@fedoraproject.org>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. moduleauthor:: Ralph Bean <rbean@redhat.com>
.. moduleauthor:: Xavier Lamien <laxathom@fedoraproject.org>
"""
# import itertools
# import urllib

from flufl.enum import IntEnum
from munch import Munch
# from kitchen.text.converters import to_bytes

from six.moves.urllib_parse import urlencode, quote

try:
    import libravatar
except ImportError:
    libravatar = None

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

from fedora.client import (
    AppError, BaseClient, FasProxyClient,
    FedoraClientError, FedoraServiceError
)

from fedora import __version__

FAS_BASE_URL = 'http://localhost:6543/'


class FASError(FedoraClientError):
    """FAS Error"""
    pass


class CLAError(FASError):
    """CLA Error"""
    pass


class AccessDenied(FASError):
    pass


USERFIELDS = [
    'affiliation', 'bugzilla_email', 'certificate_serial',
    'comments', 'country_code', 'creation', 'email', 'emailtoken',
    'facsimile', 'gpg_keyid', 'human_name', 'id', 'internal_comments',
    'ircnick', 'latitude', 'last_seen', 'longitude', 'password',
    'password_changed', 'passwordtoken', 'postal_address', 'privacy',
    'locale', 'ssh_key', 'status', 'status_change', 'telephone',
    'unverified_email', 'timezone', 'username', 'security_question',
    'security_answer', ]


class BaseStatus(IntEnum):
    INACTIVE = 0x00
    ACTIVE = 0x01
    PENDING = 0x03
    LOCKED = 0x05
    LOCKED_BY_ADMIN = 0x06
    DISABLED = 0x08


class AccountStatus(BaseStatus):
    ON_VACATION = 0x04


class GroupStatus(BaseStatus):
    ARCHIVED = 0x0A


class MembershipStatus(IntEnum):
    UNAPPROVED = 0x00
    APPROVED = 0x01
    PENDING = 0x02


class LicenseAgreementStatus(IntEnum):
    DISABLED = 0x00
    ENABLED = 0x01


class MembershipRole(IntEnum):
    UNKNOWN = 0x00
    USER = 0x01
    EDITOR = 0x02
    SPONSOR = 0x03
    ADMINISTRATOR = 0x04


class AccountActivityType(IntEnum):
    LOGGED_IN = 0x01
    ACCOUNT_UPDATE = 0x03
    REQUESTED_API_KEY = 0x04
    UPDATED_PASSWORD = 0x05
    ASKED_RESET_PASSWORD = 0x06
    RESET_PASSWORD = 0x07
    SIGNED_LICENSE = 0x0A
    REVOKED_GROUP_MEMBERSHIP = 0x0B
    REVOKED_LICENSE = 0x0C
    REQUESTED_GROUP_MEMBERSHIP = 0x0D
    NEW_GROUP_MEMBERSHIP = 0x0E
    PROMOTED_GROUP_MEMBERSHIP = 0x0F
    DOWNGRADED_GROUP_MEMBERSHIP = 0x10
    REMOVED_GROUP_MEMBERSHIP = 0x11
    REVOKED_GROUP_MEMBERSHIP_BY_ADMIN = 0x12
    CHANGED_GROUP_MAIN_ADMIN = 0x13


class ApiStatus(IntEnum):
    SUCCESS = 0x00
    FAILED = 0x01


class AccountSystem(BaseClient):
    """An object for querying the Fedora Account System.

    The Account System object provides a python API for talking to the Fedora
    Account System.  It abstracts the http requests, cookie handling, and
    other details so you can concentrate on the methods that are important to
    your program.

    .. warning::

        If your code is trying to use the AccountSystem object to
        connect to fas for multiple users you probably want to use
        :class:`~fedora.client.FasProxyClient` instead.  If your code is
        trying to reuse a single instance of AccountSystem for multiple users
        you *definitely* want to use :class:`~fedora.client.FasProxyClient`
        instead.  Using AccountSystem in these cases may result in a user
        being logged in as a different user.  (This may be the case even if
        you instantiate a new AccountSystem object for each user if
        :attr:cache_session: is True since that creates a file on the file
        system that can end up loading session credentials for the wrong
        person.

    .. versionchanged:: 0.3.26
        Added :meth:`~fedora.client.AccountSystem.gravatar_url` that returns
        a url to a gravatar for a user.
    .. versionchanged:: 0.3.33
        Renamed :meth:`~fedora.client.AccountSystem.gravatar_url` to
        :meth:`~fedora.client.AccountSystem.avatar_url`.
    .. versionchanged:: 0.4.0
        New web service (REST API)
        Refactored whole function
    """
    # proxy is a thread-safe connection to the fas server for verifying
    # passwords of other users
    proxy = None

    # size that we allow to request from remote avatar providers.
    _valid_avatar_sizes = (32, 64, 140)
    # URLs for remote avatar providers.
    _valid_avatar_services = ['libravatar', 'gravatar']

    def __init__(self, base_url=FAS_BASE_URL, token_api=None, *args, **kwargs):
        """
        Create the AccountSystem client object.

        :kwargs base_url: Base of every URL used to contact the server.
            Defaults to the Fedora Project FAS instance.
        :kwargs useragent: useragent string to use.  If not given, default to
            "Fedora Account System Client/VERSION"
        :kwargs debug: If True, log debug information
        :kwargs username: username for establishing authenticated connections
        :kwargs password: password to use with authenticated connections
        :kwargs session_cookie: **Deprecated** Use session_id instead.
            User's session_cookie to connect to the server
        :kwargs session_id: user's session_id to connect to the server
        :kwargs cache_session: if set to true, cache the user's session cookie
            on the filesystem between runs.
        """
        self.token_api = token_api
        if 'useragent' not in kwargs:
            kwargs['useragent'] = \
                'Fedora Account System Client/%s' % __version__

        super(AccountSystem, self).__init__(base_url, *args, **kwargs)
        # We need a single proxy for the class to verify username/passwords
        # against.
        if not self.proxy:
            self.proxy = FasProxyClient(base_url, useragent=self.useragent,
                                        session_as_cookie=False,
                                        debug=self.debug,
                                        insecure=self.insecure)

    ### Set insecure properly ###
    # When setting insecure, we have to set it both on ourselves and on
    # self.proxy
    def _get_insecure(self):
        return self._insecure

    def _set_insecure(self, insecure):
        self._insecure = insecure
        self.proxy = FasProxyClient(self.base_url, useragent=self.useragent,
                                    session_as_cookie=False, debug=self.debug,
                                    insecure=insecure)
        return insecure

    #: If this attribute is set to True, do not check server certificates
    #: against their CA's.  This means that man-in-the-middle attacks are
    #: possible. You might turn this option on for testing against a local
    #: version of a server with a self-signed certificate but it should be off
    #: in production.
    insecure = property(_get_insecure, _set_insecure)

    def __send_request__(self, api_method, method='GET',
                         params=None, auth_params=None):
        """
        Request an HTTP request from given

        :param api_method: API method to call on the server.
        :type api_method: unicode
        :return: HTTP's response data from server.
        :rtype: Munch
        """
        data = None
        req_params = dict()
        req_params['apikey'] = self.token_api

        if params is not None and method == 'GET':
            for key, value in params.iteritems():
                req_params[key] = value
        else:
            data = params

        resp = self.send_request(
            api_method,
            req_params=req_params,
            data=data,
            req_method=method,
            auth_params=auth_params
        )

        if 'Error' in resp:
            raise AppError(
                name=resp.Error.name,
                message=resp.Error.text
            )

        return resp

    def request_login(self, credentials):
        """
        Retrieve groups' types

        :return: Registered groups' types
        :rtype: Munch
        """
        resp = self.__send_request__('api/group/types', method='GET')

        return resp.GroupTypes

    def create_group(self, name, display_name, owner, group_type,
                     invite_only=0, needs_sponsor=0, user_can_remove=True,
                     joinmsg='', apply_rules='None', description='',
                     web_link='', mailing_list='', mailing_list_url='',
                     irc_channel='', irc_network='', parent_group=-1,
                     is_private=False, certificate=-1, license=-1):
        """
        Creates a FAS group.

        :arg name: The short group name (alphanumeric only).
        :arg display_name: A longer version of the group's name.
        :arg owner: The username of the FAS account which owns the new group.
        :arg group_type: The kind of group being created. Current valid options
            are git, svn, hg, shell, and tracking.
        :kwarg invite_only: Users must be invited to the group, they cannot
            join on their own.
        :kwarg needs_sponsor: Users must be sponsored into the group.
        :kwarg user_can_remove: Users can remove themselves from the group.
        :kwarg prerequisite: Users must be in the given group (string) before
            they can join the new group.
        :kwarg joinmsg: A message shown to users when they apply to the group.
        :kwarg apply_rules: Rules for applying to the group, shown to users
            before they apply.
        :rtype: :obj:`munch.Munch`
        :returns: A Munch containing information about the group that was
            created.

        .. versionadded:: 0.3.29
        """
        req_params = {
            'name': name,
            'display_name': display_name,
            'owner_id': owner,
            'group_type': group_type,
            'invite_only': invite_only,
            'need_approval': needs_sponsor,
            'self_removal': user_can_remove,
            'parent_group_id': parent_group,
            'join_msg': joinmsg,
            'apply_rules': apply_rules,
            'description': description,
            'web_link': web_link,
            'mailing_list': mailing_list,
            'mailing_list_url': mailing_list_url,
            'irc_channel': irc_channel,
            'irc_network': irc_network,
            'private': is_private,
            'certificate': certificate,
            'license_sign_up': license
        }

        request = self.__send_request__(
            'api/group/create', params=req_params, method='POST')
        return request

    def update_group(self, group):
        """
        Update a given group into FAS

        :param group: Group object to update
        :type group: Munch
        :return: updated group's object
        :rtype: Munch

        .. Example::

            >>> fas = AccountSystem(token_api='e533af492c7d')
            >>> group = fas.get_group_by_name('packagers')
            >>> group.irc_channel
            u'#fedora-packagers'
            >>> group.invite_only = True
            >>> group.irc_channel = u'#fedora-devel'
            >>> update_group(group)
            True
        """
        params = group.toDict()

        resp = self.__send_request__(
            'api/group/id/%s' % str(group.id), params=params, method='POST'
        )

        if resp.Status == ApiStatus.SUCCESS:
            return True

        return False

    def get_group_by_id(self, group_id):
        """
        Retrieves a group from a given group's ID.

        :param group_id: FAS group id to look up
        :type group_id: int
        :return: Returns a group object
        :rtype: Munch
        """
        response = self.__send_request__('api/group/id/%s' % group_id)

        return response.Group

    def get_group_by_name(self, group_name):
        """
        Retrieves a group's data from a given group's name

        :param group_name: A group's name to look up
        :type group_name: basestring
        :return: Returns a group object
        :rtype: Munch
        """
        response = self.__send_request__('api/group/name/%s' % group_name)

        return response.Groups

    def get_groups(self, status=None, page=1):
        """
        Retrieves list of registered groups' data.

        :param status: Group status to look up
        :type status: GroupStatus
        :return: Returns a list of registered group's object
        :rtype: Munch

        .. Example::

            >>> fas = AccountSystem(token_api='e533af492c7d')
            >>> ret = fas.get_groups(GroupStatus.ACTIVE, page=3)
            >>> ret.Pages.total
            10
            >>> groups = ret.Groups
            >>> groups[0].keys()
            [u'name', u'status', u'owner_id', u'members', u'display_name', ...]
            >>> groups[0].name
            u'fas-admin'

        """
        params = dict()

        if status is not None:
            params['status'] = status.value
        elif page > 1:
            params['page'] = page

        resp = self.__send_request__('api/groups', params=params)

        return resp

    def get_group_members(self, groupname):
        """
        Retrieves list of approved members from given FAS group.

        This method returns a list of people who are in the requested group.
        The people are all approved in the group.  Unapproved people are not
        shown.

        role_type can be one of 'user', 'sponsor', or 'administrator'.

        .. versionadded:: 0.3.2
        .. versionchanged:: 0.3.21
            Return a Bunch instead of a DictContainer
        """
        group = self.get_group_by_name(groupname)

        return group.members

    def grant_membership(self, group_id, person_id, sponsor_id=-1):
        """
        Grants pending membership request and sponsors a person if
        group requires sponsorship.

        :param group_id: Group ID to look up for membership approval.
        :type group_id: int
        :param person_id: Person ID to approve.
        :type person_id: int
        :param sponsor_id: Sponsor ID to set upon membership approval.
        This parameter should be set from 3rd party if group requires sponsorship.
        :type sponsor_id: int
        :return: Updated group's info if person has been successfully
        approved and/or sponsored
        :rtype: Munch
        """
        param = {'sponsor': sponsor_id} if sponsor_id > -1 else None

        resp = self.__send_request__(
            'api/group/%s/membership/grant/%s' % (group_id, person_id),
            params=param,
            method='POST'
        )
        if resp.Status == ApiStatus.SUCCESS:
            return resp.Group

        return None

    def update_membership_role(self, membership_id, role, requester=None):
        """
        Updates a given group's membership info

        :param membership_id: group's membership to update
        :type membership_id: Munch of membership
        :param role: role's membership to update
        :type role: fedora.client.fas2.MembershipRole
        :return: True if group's mebership has been successfully updated.
        otherwise false.
        :rtype: bool

        .. Example::

            >>> fas = SystemAccount(apikey='23d3dk32d-2k32d')
            >>> group = fas.get_group_by_name('suicide_squad')
            >>> member = group.members[0]
            >>> group = fas.update_membership_role(
            ... member.membership_id,
            ... MembershipRole.SPONSOR)
        """
        param = {'role': role.value}
        if requester is not None:
            param['admin'] = requester

        resp = self.__send_request__(
            'api/group/membership/edit/%s' % membership_id,
            params=param,
            method='POST'
        )

        if resp.Status == ApiStatus.SUCCESS:
            return resp.Group

        return None

    ### People ###

    def get_people(self, status=None, page=1):
        """
        Retrieves list of registered Fedora Contributors.

        :param status: An account status to look up (optional)
        :type status: fedora.client.fas2.AccountStatus
        :param page: A page number to look up from returned page's zise.
        :return: Returns a paginated list of person object
        :rtype: Munch

        .. versionadded:: 0.4.0
        """
        params = dict()

        if status is not None:
            params['status'] = status.value
        elif page > 1:
            params['page'] = page

        resp = self.__send_request__('api/people', params=params)

        return resp

    def get_person_by_id(self, person_id):
        """
        Retrieves a person from a given person's ID.

        :param person_id: A person's id to look up
        :type person_id: int
        :return: Returns a person object
        :rtype: Munch

        .. versionaddded:: 0.4.0
        """
        resp = self.__send_request__('api/people/id/%s' % person_id)

        return resp.People

    def get_person_by_username(self, username):
        """
        Retrieves a person from a given username.

        :param username: A people's username to look up
        :type username: basestring
        :return: Returns a person object
        :rtype: Munch

        .. versionadded:: 0.4.0
        """
        request = self.__send_request__('api/people/username/%s' % username)

        return request.People

    # def get_user_id(self):
    #     """Returns a dict relating user IDs to usernames"""
    #     request = self.send_request('json/user_id', auth=True)
    #     people = {}
    #     for person_id, username in request['people'].items():
    #         # change userids from string back to integer
    #         people[int(person_id)] = username
    #     return people

    def get_person_by_email(self, email):
        """
        Retrieves a person from a given email.

        :param email: An email to look up
        :type email: basestring
        :return: returns a person object
        :rtype: Munch

        .. versionadded:: 0.4.0
        """
        resp = self.__send_request__('api/people/email/%s' % email)

        return resp.People

        # def get_people_by_key(self, key=u'username', search=u'*', fields=None):
        #     """
        #     Return a dict of people
        #
        #     For example:
        #
        #         >>> ret_val = FASCLIENT.get_people_by_key(
        #         ...     key='email', search='toshio*', fields='id')
        #         >>> ret_val.keys()
        #         a.badger@[...].com
        #         a.badger+test1@[...].com
        #         a.badger+test2@[...].com
        #         >>> ret_val.values()
        #         100068
        #         102023
        #         102434
        #
        #     :kwarg key: Key used to organize the returned dictionary.  Valid values

        #         are 'id', 'username', or 'email'.  Default is 'username'.
        #     :kwarg search: Pattern to match usernames against.  Defaults to the
        #         '*' wildcard which matches everyone.
        #     :kwarg fields: Limit the data returned to a specific list of fields.
        #         The default is to retrieve all fields.
        #         Valid fields are:
        #
        #             * affiliation
        #             * alias_enabled
        #             * bugzilla_email
        #             * certificate_serial
        #             * comments
        #             * country_code
        #             * creation
        #             * email
        #             * emailtoken
        #             * facsimile
        #             * gpg_keyid
        #             * group_roles
        #             * human_name
        #             * id
        #             * internal_comments
        #             * ircnick
        #             * last_seen
        #             * latitude
        #             * locale
        #             * longitude
        #             * memberships
        #             * old_password
        #             * password
        #             * password_changed
        #             * passwordtoken
        #             * postal_address
        #             * privacy
        #             * roles
        #             * ssh_key
        #             * status
        #             * status_change
        #             * telephone
        #             * timezone
        #             * unverified_email
        #             * username
        #
        #         Note that for most users who access this data, many of these
        #         fields will be set to None due to security or privacy settings.
        #     :returns: a dict relating the key value to the fields.
        #
        #     .. versionchanged:: 0.3.21
        #         Return a Bunch instead of a DictContainer
        #     .. versionchanged:: 0.3.26
        #         Fixed to return a list with both people who have signed the CLA
        #         and have not
        #     """
        #     # Make sure we have a valid key value
        #     if key not in ('id', 'username', 'email'):
        #         raise KeyError('key must be one of "id", "username", or'
        #                        ' "email"')
        #
        #     if fields:
        #         fields = list(fields)
        #         for field in fields:
        #             if field not in USERFIELDS:
        #                 raise KeyError('%(field)s is not a valid field to'
        #                                ' filter' % {'field': to_bytes(field)})
        #     else:
        #         fields = USERFIELDS
        #
        #     # Make sure we retrieve the key value
        #     unrequested_fields = []
        #     if key not in fields:
        #         unrequested_fields.append(key)
        #         fields.append(key)
        #     if 'bugzilla_email' in fields:
        #         # Need id and email for the bugzilla information
        #         if 'id' not in fields:
        #             unrequested_fields.append('id')
        #             fields.append('id')
        #         if 'email' not in fields:
        #             unrequested_fields.append('email')
        #             fields.append('email')
        #
        #     request = self.send_request(
        #         '/user/list',
        #         req_params={
        #             'search': search,
        #             'fields': [f for f in fields if f != 'bugzilla_email']
        #         },
        #         auth=True)
        #
        #     people = Munch()
        #     for person in itertools.chain(request['people'],
        #                                   request['unapproved_people']):
        #         # Retrieve bugzilla_email from our list if necessary
        #         if 'bugzilla_email' in fields:
        #             if person['id'] in self.__bugzilla_email:
        #                 person['bugzilla_email'] = \
        #                     self.__bugzilla_email[person['id']]
        #             else:
        #                 person['bugzilla_email'] = person['email']
        #
        #         person_key = person[key]
        #         # Remove any fields that weren't requested by the user
        #         if unrequested_fields:
        #             for field in unrequested_fields:
        #                 del person[field]
        #
        #         # Add the person record to the people dict
        #         people[person_key] = person
        #
        #     return people

        ### Utils ###

        # def people_by_groupname(self, groupname):
        #     """Return a list of persons for the given groupname.
        #
        #     :arg groupname: Name of the group to look up
        #     :returns: A list of person objects from the group.  If the group
        #         contains no entries, then an empty list is returned.
        #     """
        #     people = self.people_by_id()
        #     group = dict(self.group_by_name(groupname))
        #     userids = [user[u'person_id'] for user in
        #                group[u'approved_roles'] + group[u'unapproved_roles']]
        #     return [people[userid] for userid in userids]

        ### Configs ###

        # def get_config(self, username, application, attribute):
        #     """Return the config entry for the key values.
        #
        #     :arg username: Username of the person
        #     :arg application: Application for which the config is set
        #     :arg attribute: Attribute key to lookup
        #     :raises AppError: if the server returns an exception
        #     :returns: The unicode string that describes the value.  If no entry
        #         matched the username, application, and attribute then None is
        #         returned.
        #     """
        #     request = self.send_request('config/list/%s/%s/%s' %
        #                                 (username, application, attribute),
        #                                 auth=True)
        #     if 'exc' in request:
        #         raise AppError(
        #             name=request['exc'],
        #             message=request['tg_flash']
        #         )
        #
        #     # Return the value if it exists, else None.
        #     if 'configs' in request and attribute in request['configs']:
        #         return request['configs'][attribute]
        #     return None

        # def get_configs_like(self, username, application, pattern=u'*'):
        #     """Return the config entries that match the keys and the pattern.
        #
        #     Note: authentication on the server will prevent anyone but the user
        #     or a fas admin from viewing or changing their configs.
        #
        #     :arg username: Username of the person
        #     :arg application: Application for which the config is set
        #     :kwarg pattern: A pattern to select values for.  This accepts * as a
        #         wildcard character. Default='*'
        #     :raises AppError: if the server returns an exception
        #     :returns: A dict mapping ``attribute`` to ``value``.
        #     """
        #     request = self.send_request(
        #         'config/list/%s/%s/%s' %
        #         (username, application, pattern),
        #         auth=True)
        #     if 'exc' in request:
        #         raise AppError(
        #             name=request['exc'],
        #             message=request['tg_flash'])
        #
        #     return request['configs']

        # def set_config(self, username, application, attribute, value):
        #     """Set a config entry in FAS for the user.
        #
        #     Note: authentication on the server will prevent anyone but the user
        #     or a fas admin from viewing or changing their configs.
        #
        #     :arg username: Username of the person
        #     :arg application: Application for which the config is set
        #     :arg attribute: The name of the config key that we're setting
        #     :arg value: The value to set this to
        #     :raises AppError: if the server returns an exception
        #     """
        #     request = self.send_request(
        #         'config/set/%s/%s/%s' %
        #         (username, application, attribute),
        #         req_params={'value': value}, auth=True)
        #
        #     if 'exc' in request:
        #         raise AppError(
        #             name=request['exc'],
        #             message=request['tg_flash'])

        # def people_query(self, constraints=None, columns=None):
        #     """Returns a list of dicts representing database rows
        #
        #     :arg constraints: A dictionary specifying WHERE constraints on
        # columns
        #     :arg columns: A list of columns to be selected in the query
        #     :raises AppError: if the query failed on the server (most likely
        #         because  the server was given a bad query)
        #     :returns: A list of dicts representing database rows (the keys of
        #         the dict are the columns requested)
        #
        #     .. versionadded:: 0.3.12.1
        #     """
        #     if constraints is None:
        #         constraints = {}
        #     if columns is None:
        #         columns = []
        #
        #     req_params = {}
        #     req_params.update(constraints)
        #     req_params['columns'] = ','.join(columns)
        #
        #     try:
        #         request = self.send_request(
        #             'json/people_query',
        #             req_params=req_params, auth=True)
        #         if request['success']:
        #             return request['data']
        #         else:
        #             raise AppError(message=request['error'], name='FASError')
        #     except FedoraServiceError:
        #         raise

        ### Certs ###

        # def user_gencert(self):
        #     """Generate a cert for a user"""
        #     try:
        #         request = self.send_request('user/dogencert', auth=True)
        #     except FedoraServiceError:
        #         raise
        #     if not request['cla']:
        #         raise CLAError
        #     return "%(cert)s\n%(key)s" % request
        #
        # ### Passwords ###
        #
        # # def verify_password(self, username, password):
        # #     """Return whether the username and password pair are valid.
        # #
        # #     :arg username: username to try authenticating
        # #     :arg password: password for the user
        # #     :returns: True if the username/password are valid.  False otherwise.

        # #     """
        # #     return self.proxy.verify_password(username, password)
