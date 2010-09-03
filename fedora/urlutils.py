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
Functions to manipulate urls.

.. versionadded:: 0.3.17

.. moduleauthor:: John (J5) Palmieri <johnp@redhat.com>
.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

from urlparse import urlparse, urlunparse
from urllib import urlencode

from kitchen.iterutils import isiterable

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs


def update_qs(uri, new_params, overwrite=True):
    '''Helper function for updating query string values.
    
    Similar to calling update on a dictionary except we modify the query
    string of the uri instead of another dictionary.

    :arg uri: URI to modify
    :arg new_params: Dict of new query parameters to add.
    :kwarg overwrite: If True (default), any old query parameter with the same
        name as a new query parameter will be overwritten.  If False, the new
        query parameters will be appended to a list with the old parameters at
        the start of the list.
    :returns: URI with the new parameters added.
    '''
    loc = list(urlparse(uri))
    query_dict = parse_qs(loc[4])
    if overwrite:
        # Overwrite any existing values with the new values
        query_dict.update(new_params)
    else:
        # Add new values in addition to the existing parameters
        # For every new entry
        for key in new_params:
            # If the entry already is present
            if key in query_dict:
                if isiterable(new_params[key]):
                    # If the new entry is a non-string iterable
                    try:
                        # Try to add the new values to the existing entry
                        query_dict[key].extend(new_params[key])
                    except AttributeError:
                        # Existing value wasn't a list, make it one
                        query_dict[key] = [query_dict[key], new_params[key]]
                else:
                    # The new entry is a scalar, so try to append it
                    try:
                        query_dict[key].append(new_params[key])
                    except AttributeError:
                        # Existing value wasn't a list, make it one
                        query_dict[key] = [query_dict[key], new_params[key]]
            else:
                # No previous entry, just set to the new entry
                query_dict[key] = new_params[key]

    # seems that we have to sanitize a bit here
    query_list = []
    for key, value in query_dict.items():
        if isiterable(value):
            for item in value:
                query_list.append((key, item))
            continue
        query_list.append((key, value))

    loc[4] = urlencode(query_list)

    return urlunparse(loc)

__all__ = ['update_qs']
