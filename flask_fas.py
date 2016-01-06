# -*- coding: utf-8 -*-
# Flask-FAS - A Flask extension for authorizing users with FAS
#
# Primary maintainer: Ian Weller <ianweller@fedoraproject.org>
#
# Copyright (c) 2012, Red Hat, Inc.
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

'''
FAS authentication plugin for the flask web framework

.. moduleauthor:: Ian Weller <ianweller@fedoraproject.org>

..versionadded:: 0.3.30
'''

print 'WARNING: flask_fas has been deprecated'
print 'The flask_fas module will disappear in the next version, please port!'
from flask_fas_openid import FAS, fas_login_required, cla_plus_one_required
