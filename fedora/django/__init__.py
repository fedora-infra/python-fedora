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
import threading

from fedora.client import ProxyClient

from django.conf import settings

connection = None

if not connection:
    connection = ProxyClient(settings.FAS_URL, settings.FAS_USERAGENT,
        session_as_cookie=False)

def person_by_id(userid):
    if not hasattr(local, 'session_id'):
        return None
    sid, userinfo = connection.send_request('json/person_by_id',
        req_params={'id': userid},
        auth_params={'session_id': local.session_id})
    return userinfo

local = threading.local()
