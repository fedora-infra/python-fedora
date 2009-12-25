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
Miscellaneous functions of use on a TurboGears 2 Server

.. versionadded:: 0.3.17

.. moduleauthor:: Toshio Kuratomi <tkuratom@redhat.com>
'''

import tg
from tg import config
from fedora.urlutils import update_qs
# We're re-exporting this from here
from fedora.tg._utils import fedora_template

tg_url = tg.url

### FIXME: Need jsonify_validation_errors, json_or_redirect, request_format
# To have all of the functions that exist for TG1

def url(*args, **kwargs):
    '''Compuiter URL

    This is a replacement for :func:`tg.controllers.url` (aka :func:`tg.url`
    in the template).  In addition to the functionality that :func:`tg.url`
    provides, it adds a token to prevent :term:`CSRF` attacks.

    The arguments and return value are the same as for :func:`tg.url`

    .. versionadded:: 0.3.17
       Added to enable :ref:`CSRF-Protection` for TG2
    '''
    # Set the current _csrf_token on the url.  It will overwrite any current
    # _csrf_token
    new_url = tg_url(*args, **kwargs)
    identity = tg.request.environ.get('repoze.who.identity')

    if identity and identity.get('_csrf_token', None):
        new_url = update_qs(new_url, {'_csrf_token': identity['_csrf_token']},
                overwrite=True)
    return new_url

def enable_csrf():
    '''A startup function to setup :ref:`CSRF-Protection`.

    This should be run at application startup.  Code like the following in the
    start-APP script or the method in :file:`commands.py` that starts it::

        from turbogears import startup
        from fedora.tg.util import enable_csrf
        startup.call_on_startup.append(enable_csrf)

    If we can get the :ref:`CSRF-Protection` into upstream :term:`TurboGears`,
    we might be able to remove this in the future.

    .. versionadded:: 0.3.17
       Added to enable :ref:`CSRF-Protection`
    '''
    # Override the tg.url function with our own
    tg.url = url
    tg.controllers.url = url

    # Ignore the _csrf_token parameter
    ignore = config.get('ignore_parameters', [])
    if '_csrf_token' not in ignore:
        ignore.append('_csrf_token')
        config.update({'ignore_parameters': ignore})

    # Add a function to the template tg stdvars that looks up a template.
    var_provider = config.get('variable_provider', None)
    if var_provider:
        config.update({'variable_provider': lambda:
            var_provider().update({'fedora_template': fedora_template})})
    else:
        config.update({'variable_provider': lambda: {'fedora_template':
            fedora_template}})

__all__ = ('enable_csrf', 'fedora_template', 'tg_url', 'url')
