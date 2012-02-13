# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2012  Ricky Zhou, Red Hat, Inc.
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
'''
Provide a client module for talking to the Fedora Account System.


.. moduleauthor:: Ricky Zhou <ricky@fedoraproject.org>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
.. moduleauthor:: Ralph Bean <rbean@redhat.com>
'''
import itertools
import urllib
import warnings

from bunch import Bunch
from kitchen.text.converters import to_bytes

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5

from fedora.client import AppError, BaseClient, FasProxyClient, \
        FedoraClientError, FedoraServiceError
from fedora import __version__, b_

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

USERFIELDS = ['affiliation', 'bugzilla_email', 'certificate_serial',
        'comments', 'country_code', 'creation', 'email', 'emailtoken',
        'facsimile', 'gpg_keyid', 'human_name', 'id', 'internal_comments',
        'ircnick', 'latitude', 'last_seen', 'longitude', 'password',
        'password_changed', 'passwordtoken', 'postal_address', 'privacy',
        'locale', 'ssh_key', 'status', 'status_change', 'telephone',
        'unverified_email', 'timezone', 'username', ]

class AccountSystem(BaseClient):
    '''An object for querying the Fedora Account System.

    The Account System object provides a python API for talking to the Fedora
    Account System.  It abstracts the http requests, cookie handling, and
    other details so you can concentrate on the methods that are important to
    your program.

    .. versionchanged:: 0.3.26
        Added :meth:`~fedora.client.AccountSystem.gravatar_url` that returns
        a url to a gravatar for a user.
    '''
    # proxy is a thread-safe connection to the fas server for verifying
    # passwords of other users
    proxy = None

    # size that we allow to request from gravatar.com
    _valid_gravatar_sizes = (32, 64, 140)

    def __init__(self, base_url='https://admin.fedoraproject.org/accounts/',
            *args, **kwargs):
        '''Create the AccountSystem client object.

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
        '''
        if 'useragent' not in kwargs:
            kwargs['useragent'] = 'Fedora Account System Client/%s' \
                    % __version__
        super(AccountSystem, self).__init__(base_url, *args, **kwargs)
        # We need a single proxy for the class to verify username/passwords
        # against.
        if not self.proxy:
            self.proxy = FasProxyClient(base_url, useragent=self.useragent,
                    session_as_cookie=False, debug=self.debug,
                    insecure=self.insecure)

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
                # Roozbeh Pournader: roozbeh@farsiweb.info
                100350: 'roozbeh@gmail.com',
                # Michael DeHaan: michael.dehaan@gmail.com
                100603: 'mdehaan@redhat.com',
                # Sebastian Gosenheimer: sgosenheimer@googlemail.com
                103647: 'sebastian.gosenheimer@proio.com',
                # Ben Konrath: bkonrath@redhat.com
                101156: 'ben@bagu.org',
                # Kai Engert: kaie@redhat.com
                100399: 'kengert@redhat.com',
                # William Jon McCann: william.jon.mccann@gmail.com
                102952: 'jmccann@redhat.com',
                # Simon Wesp: simon@w3sp.de
                109464: 'cassmodiah@fedoraproject.org',
                # Robert M. Albrecht: romal@gmx.de
                101475: 'mail@romal.de',
                # Mathieu Bridon: mathieu.bridon@gmail.com
                100753: 'bochecha@fedoraproject.org',
                # Davide Cescato: davide.cescato@iaeste.ch
                123204: 'ceski@fedoraproject.org',
                # Nick Bebout: nick@bebout.net
                101458: 'nb@fedoraproject.org',
                # Niels Haase: haase.niels@gmail.com
                126862: 'arxs@fedoraproject.org',
                # Thomas Janssen: th.p.janssen@googlemail.com
                103110: 'thomasj@fedoraproject.org',
                # Michael J Gruber: 'michaeljgruber+fedoraproject@gmail.com'
                105113: 'mjg@fedoraproject.org',
                # Juan Manuel Rodriguez Moreno: 'nushio@gmail.com'
                101302: 'nushio@fedoraproject.org',
                # Andrew Cagney: 'andrew.cagney@gmail.com'
                102169: 'cagney@fedoraproject.org',
                # Jeremy Katz: 'jeremy@katzbox.net'
                100036: 'katzj@fedoraproject.org',
                # Dominic Hopf: 'dmaphy@gmail.com'
                124904: 'dmaphy@fedoraproject.org',
                # Christoph Wickert: 'christoph.wickert@googlemail.com':
                100271: 'cwickert@fedoraproject.org',
                # Elliott Baron: 'elliottbaron@gmail.com'
                106760: 'ebaron@fedoraproject.org',
                # Thomas Spura: 'spurath@students.uni-mainz.de'
                111433: 'tomspur@fedoraproject.org',
                # Adam Miller: 'maxamillion@gmail.com'
                110673: 'maxamillion@fedoraproject.org',
                # Garrett Holmstrom: 'garrett.holmstrom@gmail.com'
                131739: 'gholms@fedoraproject.org',
                # Tareq Al Jurf: taljurf.fedora@gmail.com
                109863: 'taljurf@fedoraproject.org',
                # Josh Kayse: jokajak@gmail.com
                148243: 'jokajak@fedoraproject.org',
                # Behdad Esfahbod: fedora@behdad.org
                100102: 'behdad@fedoraproject.org',
                # Daniel Bruno: danielbrunos@gmail.com
                101608: 'dbruno@fedoraproject.org',
                # Beth Lynn Eicher: bethlynneicher@gmail.com
                148706: 'bethlynn@fedoraproject.org',
                # Andre Robatino: andre.robatino@verizon.net
                114970: 'robatino@fedoraproject.org',
                # Jeff Sheltren: jeff@tag1consulting.com
                100058: 'sheltren@fedoraproject.org',
                # Josh Boyer: jwboyer@gmail.com
                100115: 'jwboyer@redhat.com',
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

    ### Set insecure properly ###
    # When setting insecure, we have to set it both on ourselves and on
    # self.proxy
    def _get_insecure(self):
        return self._insecure

    def _set_insecure(self, insecure):
        self._insecure = insecure
        self.proxy = FasProxyClient(self.base_url, useragent=self.useragent,
                session_as_cookie=False, debug=self.debug, insecure=insecure)
        return insecure
    #: If this attribute is set to True, do not check server certificates
    #: against their CA's.  This means that man-in-the-middle attacks are
    #: possible. You might turn this option on for testing against a local
    #: version of a server with a self-signed certificate but it should be off
    #: in production.
    insecure = property(_get_insecure, _set_insecure)

    ### Groups ###

    def group_by_id(self, group_id):
        '''Returns a group object based on its id'''
        params = {'group_id': int(group_id)}
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
            raise AppError(message=b_('FAS server unable to retrieve group'
                ' %(group)s') % {'group': to_bytes(groupname)},
                name='FASError')

    def group_members(self, groupname):
        '''Return a list of people approved for a group.

        This method returns a list of people who are in the requested group.
        The people are all approved in the group.  Unapproved people are not
        shown.  The format of data is::

            \[{'username': 'person1', 'role_type': 'user'},
            \{'username': 'person2', 'role_type': 'sponsor'}]

        role_type can be one of 'user', 'sponsor', or 'administrator'.

        .. versionadded:: 0.3.2
        .. versionchanged:: 0.3.21
            Return a Bunch instead of a DictContainer
        '''
        request = self.send_request('/group/dump/%s' %
                urllib.quote(groupname), auth=True)

        return [Bunch(username=user[0], role_type=user[3])
                    for user in request['people']]

    ### People ###

    def person_by_id(self, person_id):
        '''Returns a person object based on its id'''
        person_id = int(person_id)
        params = {'person_id': person_id}
        request = self.send_request('json/person_by_id', auth=True,
                req_params=params)

        if request['success']:
            if person_id in self.__bugzilla_email:
                request['person']['bugzilla_email'] = \
                        self.__bugzilla_email[person_id]
            else:
                request['person']['bugzilla_email'] = request['person']['email']
            # In a devel version of FAS, membership info was returned separately
            # This was later corrected (can remove this code at some point)
            if 'approved' in request:
                request['person']['approved_memberships'] = request['approved']
            if 'unapproved' in request:
                request['person']['unapproved_memberships'] = \
                        request['unapproved']
            return request['person']
        else:
            return dict()

    def person_by_username(self, username):
        '''Returns a person object based on its username'''
        params = {'username': username}
        request = self.send_request('json/person_by_username', auth = True,
                req_params = params)

        if request['success']:
            person = request['person']
            if person['id'] in self.__bugzilla_email:
                person['bugzilla_email'] = self.__bugzilla_email[person['id']]
            else:
                person['bugzilla_email'] = person['email']
            # In a devel version of FAS, membership info was returned separately
            # This was later corrected (can remove this code at some point)
            if 'approved' in request:
                request['person']['approved_memberships'] = request['approved']
            if 'unapproved' in request:
                request['person']['unapproved_memberships'] = \
                        request['unapproved']
            return person
        else:
            return dict()

    def gravatar_url(self, username, size=64,
                     default=None):
        ''' Returns a URL to a gravatar for a given username.

        :arg username: FAS username to construct a gravatar url for
        :kwarg size: size of the gravatar.  Allowed sizes are 32, 64, 140.
            Default: 64
        :kwarg default: If gravatar does not have a gravatar image for the
            email address, this url is returned instead.  Default:
            the fedora logo at the specified size.
        :raises ValueError: if the size parameter is not allowed
        :rtype: :obj:`str`
        :returns: url of a gravatar for the user

        If that user has no gravatar entry, instruct gravatar.com to redirect
        us to the Fedora logo.

        If that user has no email attribute, then make a fake request to
        gravatar.

        .. versionadded:: 0.3.26
        '''
        if size not in self._valid_gravatar_sizes:
            raise ValueError(b_('Size %(size)i disallowed.  Must be in'
                ' %(valid_sizes)r') % { 'size': size,
                    'valid_sizes': self._valid_gravatar_sizes})

        if not default:
            default = "http://fedoraproject.org/static/images/" + \
                    "fedora_infinity_%ix%i.png" % (size, size)

        query_string = urllib.urlencode({
            's': size,
            'd': default,
        })

        person = self.person_by_username(username)
        email = person.get('email', 'no_email')
        hash = md5(email).hexdigest()

        return "http://www.gravatar.com/avatar/%s?%s" % (hash, query_string)

    def user_id(self):
        '''Returns a dict relating user IDs to usernames'''
        request = self.send_request('json/user_id', auth=True)
        people = {}
        for person_id, username in request['people'].items():
            # change userids from string back to integer
            people[int(person_id)] = username
        return people

    def people_by_key(self, key=u'username', search=u'*', fields=None):
        '''Return a dict of people

        :kwarg key: Key by this field.  Valid values are 'id', 'username', or
            'email'.  Default is 'username'
        :kwarg search: Pattern to match usernames against.  Defaults to the
            '*' wildcard which matches everyone.
        :kwarg fields: Limit the data returned to a specific list of fields.
            The default is to retrieve all fields.
            Valid fields are:

                * affiliation
                * alias_enabled
                * bugzilla_email
                * certificate_serial
                * comments
                * country_code
                * creation
                * email
                * emailtoken
                * facsimile
                * gpg_keyid
                * group_roles
                * human_name
                * id
                * internal_comments
                * ircnick
                * last_seen
                * latitude
                * locale
                * longitude
                * memberships
                * old_password
                * password
                * password_changed
                * passwordtoken
                * postal_address
                * privacy
                * roles
                * ssh_key
                * status
                * status_change
                * telephone
                * timezone
                * unverified_email
                * username

            Note that for most users who access this data, many of these
            fields will be set to None due to security or privacy settings.
        :returns: a dict relating the key value to the fields.

        .. versionchanged:: 0.3.21
            Return a Bunch instead of a DictContainer
        .. versionchanged:: 0.3.26
            Fixed to return a list with both people who have signed the CLA
            and have not
        '''
        # Make sure we have a valid key value
        if key not in ('id', 'username', 'email'):
            raise KeyError(b_('key must be one of "id", "username", or'
                ' "email"'))

        if fields:
            fields = list(fields)
            for field in fields:
                if field not in USERFIELDS:
                    raise KeyError(b_('%(field)s is not a valid field to'
                        ' filter') % {'field': to_bytes(field)})
        else:
            fields = USERFIELDS

        # Make sure we retrieve the key value
        unrequested_fields = []
        if key not in fields:
            unrequested_fields.append(key)
            fields.append(key)
        if 'bugzilla_email' in fields:
            # Need id and email for the bugzilla information
            if 'id' not in fields:
                unrequested_fields.append('id')
                fields.append('id')
            if 'email' not in fields:
                unrequested_fields.append('email')
                fields.append('email')

        request = self.send_request('/user/list', req_params={'search': search,
            'fields': [f for f in fields if f != 'bugzilla_email']}, auth=True)

        people = Bunch()
        for person in itertools.chain(request['people'],
                request['unapproved_people']):
            # Retrieve bugzilla_email from our list if necessary
            if 'bugzilla_email' in fields:
                if person['id'] in self.__bugzilla_email:
                    person['bugzilla_email'] = \
                            self.__bugzilla_email[person['id']]
                else:
                    person['bugzilla_email'] = person['email']

            person_key = person[key]
            # Remove any fields that weren't requested by the user
            if unrequested_fields:
                for field in unrequested_fields:
                    del person[field]

            # Add the person record to the people dict
            people[person_key] = person

        return people

    def people_by_id(self):
        '''*Deprecated* Use people_by_key() instead.

        Returns a dict relating user IDs to human_name, email, username,
        and bugzilla email

        .. versionchanged:: 0.3.21
            Return a Bunch instead of a DictContainer
        '''
        warnings.warn(b_("people_by_id() is deprecated and will be removed in"
            " 0.4.  Please port your code to use people_by_key(key='id',"
            " fields=['human_name', 'email', 'username', 'bugzilla_email'])"
            " instead"), DeprecationWarning, stacklevel=2)

        request = self.send_request('/json/user_id', auth=True)
        user_to_id = {}
        people = Bunch()
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

    ### Utils ###

    def people_by_groupname(self, groupname):
        '''Return a list of persons for the given groupname.

        :arg groupname: Name of the group to look up
        :returns: A list of person objects from the group.  If the group
            contains no entries, then an empty list is returned.
        '''
        people = self.people_by_id()
        group = dict(self.group_by_name(groupname))
        userids = [user[u'person_id'] for user in
                   group[u'approved_roles'] + group[u'unapproved_roles']]
        return [people[userid] for userid in userids]

    ### Configs ###

    def get_config(self, username, application, attribute):
        '''Return the config entry for the key values.

        :arg username: Username of the person
        :arg application: Application for which the config is set
        :arg attribute: Attribute key to lookup
        :raises AppError: if the server returns an exception
        :returns: The unicode string that describes the value.  If no entry
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

        :arg username: Username of the person
        :arg application: Application for which the config is set
        :kwarg pattern: A pattern to select values for.  This accepts * as a
            wildcard character. Default='*'
        :raises AppError: if the server returns an exception
        :returns: A dict mapping ``attribute`` to ``value``.
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

        :arg username: Username of the person
        :arg application: Application for which the config is set
        :arg attribute: The name of the config key that we're setting
        :arg value: The value to set this to
        :raises AppError: if the server returns an exception
        '''
        request = self.send_request('config/set/%s/%s/%s' %
                (username, application, attribute),
                req_params={'value': value}, auth=True)

        if 'exc' in request:
            raise AppError(name = request['exc'], message = request['tg_flash'])

    def people_query(self, constraints=None, columns=None):
        '''Returns a list of dicts representing database rows

        :arg constraints: A dictionary specifying WHERE constraints on columns
        :arg columns: A list of columns to be selected in the query
        :raises AppError: if the query failed on the server (most likely
            because  the server was given a bad query)
        :returns: A list of dicts representing database rows (the keys of
            the dict are the columns requested)

        .. versionadded:: 0.3.12.1
        '''
        if constraints is None:
            constraints = {}
        if columns is None:
            columns = []

        req_params = {}
        req_params.update(constraints)
        req_params['columns'] = ','.join(columns)

        try:
            request = self.send_request('json/people_query',
                req_params=req_params, auth=True)
            if request['success']:
                return request['data']
            else:
                raise AppError(message=request['error'], name='FASError')
        except FedoraServiceError:
            raise

    ### Certs ###

    def user_gencert(self):
        '''Generate a cert for a user'''
        try:
            request = self.send_request('user/dogencert', auth=True)
        except FedoraServiceError:
            raise
        if not request['cla']:
            raise CLAError
        return "%(cert)s\n%(key)s" % request

    ### Passwords ###

    def verify_password(self, username, password):
        '''Return whether the username and password pair are valid.

        :arg username: username to try authenticating
        :arg password: password for the user
        :returns: True if the username/password are valid.  False otherwise.
        '''
        return self.proxy.verify_password(username, password)

    ### fasClient Special Methods ###

    def group_data(self, force_refresh=None):
        '''Return administrators/sponsors/users and group type for all groups

        :arg force_refresh: If true, the returned data will be queried from the
            database, as opposed to memcached.
        :raises AppError: if the query failed on the server
        :returns: A dict mapping group names to the group type and the
            user IDs of the administrator, sponsors, and users of the group.

        .. versionadded:: 0.3.8
        '''
        params = {}
        if force_refresh:
            params['force_refresh'] = True

        try:
            request = self.send_request('json/fas_client/group_data',
                req_params=params, auth=True)
            if request['success']:
                return request['data']
            else:
                raise AppError(message=b_('FAS server unable to retrieve'
                    ' group members'), name='FASError')
        except FedoraServiceError:
            raise

    def user_data(self):
        '''Return user data for all users in FAS

        Note: If the user is not authorized to see password hashes,
        '*' is returned for the hash.

        :raises AppError: if the query failed on the server
        :returns: A dict mapping user IDs to a username, password hash,
            SSH public key, email address, and status.

        .. versionadded:: 0.3.8
        '''
        try:
            request = self.send_request('json/fas_client/user_data', auth=True)
            if request['success']:
                return request['data']
            else:
                raise AppError(message=b_('FAS server unable to retrieve user'
                    ' information'), name='FASError')
        except FedoraServiceError:
            raise

