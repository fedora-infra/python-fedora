# -*- coding: utf-8 -*-
#
# Copyright (C) 2009  Ignacio Vazquez-Abrams
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
.. moduleauthor:: Ignacio Vazquez-Abrams <ivazquez@fedoraproject.org>
'''
from fedora.client import AuthError
from fedora.django import connection, person_by_id
from fedora import _

import django.contrib.auth.models as authmodels
from django.conf import settings

# Map FAS user elements to model attributes
_fasmap = {
    'id': 'id',
    'username': 'username',
    'email': 'email',
}

def _new_group(group):
    try:
        g = authmodels.Group.objects.get(id=group['id'])
    except authmodels.Group.DoesNotExist:
        g = authmodels.Group(id=group['id'])
    g.name = group['name']
    g.save()
    return g

def _syncdb_handler(sender, **kwargs):
    # Import FAS groups
    verbosity = kwargs.get('verbosity', 1)
    if verbosity > 0:
        print _('Loading FAS groups...')
    try:
        gl = connection.send_request('group/list', 
            auth_params={'username': settings.FAS_USERNAME,
            'password': settings.FAS_PASSWORD})
    except AuthError:
        if verbosity > 0:
            print _('Unable to load FAS groups. Did you set '
                'FAS_USERNAME and FAS_PASSWORD?')
    else:
        groups = gl['groups']
        for group in groups:
            _new_group(group)
        if verbosity > 0:
            print _('FAS groups loaded. Don\'t forget to unset '
                'FAS_USERNAME and FAS_PASSWORD.')

class FasUserManager(authmodels.UserManager):
    def user_from_fas(self, user):
        """
        Creates a user in the table based on the structure returned
        by FAS
        """
        d = {}
        for k, v in _fasmap.iteritems():
            d[v] = user[k]
        u = FasUser(**d)
        u.set_unusable_password()
        u.is_active = user['status'] == 'active'
        admin = (user['username'] in
            getattr(settings, 'FAS_ADMINS', ()))
        u.is_staff = admin
        u.is_superuser = admin
        if getattr(settings, 'FAS_GENERICEMAIL', True):
            u.email = u._get_email()
        u.save()
        for group in user['approved_memberships']:
            g = _new_group(group)
            u.groups.add(g)
        u.save()
        return u

class FasUser(authmodels.User):
    def _get_name(self):
        userinfo = person_by_id(self.id)
        return userinfo['human_name']

    def _get_email(self):
        return '%s@fedoraproject.org' % self.username

    name = property(_get_name)

    objects = FasUserManager()

    def get_full_name(self):
        return self.name.strip()
