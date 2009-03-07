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
from fedora.django import local
from fedora.django.auth.models import FasUser

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
        if isinstance(request.user, AnonymousUser):
#            response.set_cookie(key='tg-visit', value='', max_age=0)
            if 'tg-visit' in request.session:
                del request.session['tg-visit']
        else:
            request.session['tg-visit'] = local.session_id
#            response.set_cookie(key='tg-visit',
#                value=local.session_id, max_age=0)
        return response
