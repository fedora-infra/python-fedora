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
from fedora.django import local

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import AnonymousUser

class FasMiddleware(object):
    def process_request(self, request):
#        tgvisit = request.COOKIES.get('tg-visit', None)
        tgvisit = request.session.get('tg-visit', None)
        if tgvisit:
            user = authenticate(session_id=tgvisit)
            if user:
                try:
                    login(request, user)
                except AuthError:
                    logout(request)

    def process_response(self, request, response):
        if response.status_code != 301:
            if isinstance(request.user, AnonymousUser):
#                response.set_cookie(key='tg-visit', value='', max_age=0)
                if 'tg-visit' in request.session:
                    del request.session['tg-visit']
            else:
                request.session['tg-visit'] = local.session_id
#               response.set_cookie(key='tg-visit',
#                   value=local.session_id, max_age=0)
        return response
