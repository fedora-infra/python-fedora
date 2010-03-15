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
            session_id, userinfo = connection.get_user_info(auth_params=auth)
            user = FasUser.objects.user_from_fas(userinfo)
            user.session_id = session_id
            if user.is_active:
                return user
        except AuthError:
            pass

    def get_user(self, userid):
        try:
            userinfo = person_by_id(userid)
            if userinfo:
                return FasUser.objects.user_from_fas(userinfo)
        except AuthError:
            return AnonymousUser()
