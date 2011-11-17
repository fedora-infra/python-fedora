# -*- coding: utf-8 -*-
#
# Copyright (C) 2009  Ignacio Vazquez-Abrams
# Copyright (C) 2011  Red Hat, Inc
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

.. note:: Toshio only added httponly cookie support

.. versionchanged:: 0.3.26
    Made session cookies httponly
'''
from fedora.client import AuthError

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import AnonymousUser

class FasMiddleware(object):
    def process_request(self, request):
        # Retrieve the sessionid that the user gave, associating them with the
        # account system session
        sid = request.COOKIES.get('tg-visit', None)

        # Check if the session is still valid
        authenticated = False
        if sid:
            user = authenticate(session_id=sid)
            if user:
                try:
                    login(request, user)
                    authenticated = True
                except AuthError:
                    pass

        if not authenticated:
            # Hack around misthought out djiblits/django interaction;
            # If we're logging in in django and get to here without having
            # the second factor of authentication, we need to logout the
            # django kept session information.  Since we can't know precisely
            # what private information django might be keeping we need to use
            # django API to remove everything.  However, djiblits requires the
            # request.session.test_cookie_worked() function in order to log
            # someone in later.  The django logout function has removed that
            # function from the session attribute so the djiblit login fails.
            #
            # Save the necessary pieces of the session architecture here
            cookie_status = request.session.test_cookie_worked()
            logout(request)
            # python doesn't have closures
            if cookie_status:
                request.session.test_cookie_worked = lambda: True
            else:
                request.session.test_cookie_worked = lambda: False
            request.session.delete_test_cookie = lambda: None

    def process_response(self, request, response):
        if response.status_code != 301:
            if isinstance(request.user, AnonymousUser):
                response.set_cookie(key='tg-visit', value='', max_age=0)
                if 'tg-visit' in request.session:
                    del request.session['tg-visit']
            else:
                try:
                    response.set_cookie('tg-visit',
                            request.user.session_id, max_age=1814400,
                            path='/', secure=True, httponly=True)
                except AttributeError, e:
                    # We expect that request.user.session_id won't be set
                    # if the user is logging in with a non-FAS account
                    # (ie: Django local auth).
                    pass
        return response
