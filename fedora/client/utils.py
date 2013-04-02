#!/usr/bin/python -tt
# -*- coding: utf-8 -*-
#
# Copyright 2013  Red Hat, Inc.
# This file is part of python-fedora
#·
# python-fedora is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#·
# python-fedora is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#·
# You should have received a copy of the GNU Lesser General Public
# License along with python-fedora; if not, see <http://www.gnu.org/licenses/>
#
'''
Common functions used by clients (interfaces) web service.

.. versionadded:: 0.3.29
'''

def filter_password(password):
    '''
    Filter out password key type.
    
    Argument:
    :password: Given password string.
               Password string could be password only or
               password+token.
    :returns: All token found from given password key.
    '''
    token = None
    # Check if we have more than one password key from the string
    if password > 44:
        # If so, we expect an otp key format at end
        if password[-44:].startswith('ccccc'):
            token = password[-44:]
            password = password[:-44]
            print 'Found token from password field: %s' % token
    
    return password, token
