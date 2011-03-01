# -*- coding: utf-8 -*-
#
# Copyright (C) 2010  Red Hat, Inc.
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
Functions to manipulate unicode and byte strings

.. versionadded:: 0.3.17
.. versionchanged:: 0.3.22
    Deprecate in favor of kitchen.text.converters

.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''
import warnings
from kitchen.text.converters import to_unicode, to_bytes

from fedora import b_

warnings.warn(b_('fedora.textutils is deprecated.  Use'
    ' kitchen.text.converters instead'), DeprecationWarning, stacklevel=2)

__all__ = ('to_unicode', 'to_bytes')
