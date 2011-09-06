# -*- coding: utf-8 -*-
#
# Copyright (C) 2011  Red Hat, Inc.
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
Miscellaneous functions of use on a TurboGears Server.  This interface is
*deprecated*

.. versionchanged:: 0.3.25
    Deprecated

.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''
# Pylint Messages
# :W0401: This file is for backwards compatibility.  It has been renamed to
#   tg/utils.  We use a wildcard import just to import the names for
#   functions into this namespace.
# :W0614: Ditto.
from fedora.tg.utils import * #pylint:disable-msg=W0614,W0401
from fedora import b_

import warnings

warnings.warn(b_('fedora.tg.tg1utils is deprecated.  Switch to'
    ' fedora.tg.utils instead.  This file will disappear in 0.4'),
    DeprecationWarning, stacklevel=2)

__all__ = ('add_custom_stdvars', 'absolute_url', 'enable_csrf',
                'fedora_template', 'jsonify_validation_errors', 'json_or_redirect',
                        'request_format', 'tg_absolute_url', 'tg_url', 'url')
