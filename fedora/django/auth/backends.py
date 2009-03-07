# -*- coding: utf-8 -*-
#
# Copyright © 2009  Ignacio Vazquez-Abrams All rights reserved.
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
'''
.. moduleauthor:: Ignacio Vazquez-Abrams <ivazquez@fedoraproject.org>
'''
from fedora.client import AuthError
from fedora.django import connection, person_by_id, local
from fedora.django.auth.models import FasUser

from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.backends import ModelBackend

class FasBackend(ModelBackend):
    def authenticate(self, username=None, password=None,
        session_id=None):
        try:
            if session_id:
                auth = {'session_id': session_id}
            else:
                auth = {'username': username, 'password': password}
            session_id, userinfo = connection.send_request('user/view',
                auth_params=auth)
            local.session_id = session_id
            user = FasUser.objects.user_from_fas(userinfo['person'])
            if user.is_active:
                return user
        except AuthError:
            pass

    def get_user(self, userid):
        try:
            userinfo = person_by_id(userid)
            if userinfo:
                return FasUser.objects.user_from_fas(userinfo['person'])
        except AuthError:
            return AnonymousUser()
