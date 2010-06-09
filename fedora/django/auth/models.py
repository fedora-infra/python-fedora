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
.. moduleauthor:: Toshio Kuratomi <toshio@fedoraproject.org>
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
        gl = connection.group_list({'username': settings.FAS_USERNAME,
            'password': settings.FAS_PASSWORD})
    except AuthError:
        if verbosity > 0:
            print _('Unable to load FAS groups. Did you set '
                'FAS_USERNAME and FAS_PASSWORD?')
    else:
        groups = gl[1]['groups']
        for group in groups:
            _new_group(group)
        if verbosity > 0:
            print _('FAS groups loaded. Don\'t forget to set '
                'FAS_USERNAME and FAS_PASSWORD to a low-privilege '
                'account.')

class FasUserManager(authmodels.UserManager):
    def user_from_fas(self, user):
        """
        Creates a user in the table based on the structure returned
        by FAS
        """
        log = open('/var/tmp/django.log', 'a')
        log.write('in models user_from_fas\n')
        log.close()
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
        known_groups = []
        for group in u.groups.values():
            known_groups.append(group['id'])

        fas_groups = []
        for group in user['approved_memberships']:
            fas_groups.append(group['id'])

        # This user has been added to one or more FAS groups
        for group in (g for g in user['approved_memberships'] if g['id'] not in known_groups):
            newgroup = _new_group(group)
            u.groups.add(newgroup)

        # This user has been removed from one or more FAS groups
        for gid in known_groups:
            found = False
            for g in user['approved_memberships']:
                if g['id'] == gid:
                    found = True
                    break
            if not found:
                u.groups.remove(authmodels.Group.objects.get(id=gid))

        u.save()
        return u

class FasUser(authmodels.User):
    def _get_name(self):
        log = open('/var/tmp/django.log', 'a')
        log.write('in models _get_name\n')
        log.close()
        userinfo = person_by_id(self.id)
        return userinfo['human_name']

    def _get_email(self):
        log = open('/var/tmp/django.log', 'a')
        log.write('in models _get_email\n')
        log.close()
        return '%s@fedoraproject.org' % self.username

    name = property(_get_name)

    objects = FasUserManager()

    def get_full_name(self):
        log = open('/var/tmp/django.log', 'a')
        log.write('in models get_full_name\n')
        log.close()
        if self.name:
            return self.name.strip()
        return self.username.strip()
