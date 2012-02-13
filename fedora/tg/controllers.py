# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-2011  Red Hat, Inc.
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
Controller functions that are standard across Fedora Applications


.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''
from turbogears import flash
from turbogears import identity, redirect
from cherrypy import request, response

from fedora.tg.utils import request_format

from fedora import _

def login(forward_url=None, *args, **kwargs):
    '''Page to become authenticated to the Account System.

    This shows a small login box to type in your username and password
    from the Fedora Account System.

    To use this, replace your current login controller method with::

        from fedora.controllers import login as fc_login

        @expose(template='yourapp.yourlogintemplate', allow_json=True)
        def login(self, forward_url=None, *args, **kwargs):
            login_dict = fc_login(forward_url, args, kwargs)
            # Add anything to the return dict that you need for your app
            return login_dict

    :kwarg: forward_url: The url to send to once authentication succeeds
    '''
    if forward_url:
        if isinstance(forward_url, list):
            forward_url = forward_url.pop(0)
        else:
            del request.params['forward_url']

    if not identity.current.anonymous and identity.was_login_attempted() \
            and not identity.get_identity_errors():
        # User is logged in
        flash(_('Welcome, %s') % identity.current.user_name)
        if request_format() == 'json':
            # When called as a json method, doesn't make any sense to redirect
            # to a page.  Returning the logged in identity is better.
            return dict(user=identity.current.user,
                    _csrf_token=identity.current.csrf_token)
        redirect(forward_url or '/')

    if identity.was_login_attempted():
        msg = _('The credentials you supplied were not correct or '
               'did not grant access to this resource.')
    elif identity.get_identity_errors():
        msg = _('You must provide your credentials before accessing '
               'this resource.')
    else:
        msg = _('Please log in.')
        if not forward_url:
            forward_url = request.headers.get('Referer', '/')

    response.status = 403
    return dict(logging_in=True, message=msg,
        forward_url=forward_url, previous_url=request.path_info,
        original_parameters=request.params)

def logout(url=None):
    '''Logout from the server.

    To use this, replace your current login controller method with::

        from fedora.controllers import logout as fc_logout

        @expose(allow_json=True)
        def logout(self):
            return fc_logout()

    :kwarg url: If provided, when the user logs out, they will always be taken
        to this url.  This defaults to taking the user to the URL they were
        at when they clicked logout.
    '''
    identity.current.logout()
    flash(_('You have successfully logged out.'))
    if request_format() == 'json':
        return dict()
    if not url:
        url = request.headers.get('Referer','/')
    redirect(url)
