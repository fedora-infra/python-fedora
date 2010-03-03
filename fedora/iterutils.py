
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009  Red Hat, Inc.
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
Functions to manipulate iterables

.. versionadded:: 0.3.17

.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

def isiterable(obj, include_string=True):
    '''Check whether an object is an iterable.

    :arg obj: Object to test whether it is an iterable
    :include_string: If True (default), if `obj` is a str or unicode this
        function will return True.  If set to False, strings and unicodes will
        cause this function to return False.
    :returns: True if `obj` is iterable, otherwise False.
    '''
    if include_string or not isinstance(obj, basestring):
        try:
            iter(obj)
        except TypeError:
            return False
        else:
            return True

__all__ = ['isiterable']
