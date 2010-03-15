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
import threading

from fedora.client import FasProxyClient

from django.conf import settings

connection = None

if not connection:
    connection = FasProxyClient(base_url=settings.FAS_URL, useragent=settings.FAS_USERAGENT)

def person_by_id(userid):
    sid, userinfo = connection.person_by_id(userid,
            {'username': settings.FAS_USERNAME,
            'password': settings.FAS_PASSWORD})
    return userinfo
