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

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import AnonymousUser

class FasMiddleware(object):
    def process_request(self, request):
        tgvisit = request.COOKIES.get('tg-visit', None)
        authenticated = False
        if tgvisit:
            user = authenticate(session_id=tgvisit)
            if user:
                try:
                    login(request, user)
                    authenticated = True
                except AuthError:
                    pass
        if not authenticated:
            # set the user to unknown.  Using logout() is too heavyweight
            # here as it deletes the session as well (which some apps need for
            # storing session info even if not logged in)
            if hasattr(request, 'user'):
                request.user = AnonymousUser()

    def process_response(self, request, response):
        if response.status_code != 301:
            if isinstance(request.user, AnonymousUser):
                response.set_cookie(key='tg-visit', value='', max_age=0)
                if 'tg-visit' in request.session:
                    del request.session['tg-visit']
            else:
                try:
                    response.set_cookie('tg-visit',
                            request.user.session_id, max_age=1814400, path='/', secure=True)
                except AttributeError, e:
                    # We expect that request.user.session_id won't be set
                    # if the user is logging in with a non-FAS account
                    # (ie: Django local auth).
                    pass
        return response
