# -*- coding: utf-8 -*-
#
# Copyright (C) 2009-2011  Red Hat, Inc.
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
try:
    from hashlib import sha1 as sha_constructor
except ImportError:
    from sha import new as sha_constructor

import tg
from tg import config
from repoze.what.plugins.pylonshq import booleanize_predicates
from copy import copy
from bunch import Bunch
import logging

from fedora.wsgi.faswho import make_faswho_middleware
from fedora.urlutils import update_qs
# We're re-exporting this from here
from fedora.tg._utils import fedora_template

tg_url = tg.url

### FIXME: Need jsonify_validation_errors, json_or_redirect, request_format
# To have all of the functions that exist for TG1

def url(*args, **kwargs):
    '''Compute URL

    This is a replacement for :func:`tg.controllers.url` (aka :func:`tg.url`
    in the template).  In addition to the functionality that :func:`tg.url`
    provides, it adds a token to prevent :term:`CSRF` attacks.

    The arguments and return value are the same as for :func:`tg.url`

    The original :func:`tg.url` is accessible as
    :func:`fedora.tg.tg2utils.tg_url`

    .. versionadded:: 0.3.17
       Added to enable :ref:`CSRF-Protection` for TG2
    '''
    new_url = tg_url(*args, **kwargs)

    # Set the current _csrf_token on the url.  It will overwrite any current
    # _csrf_token
    identity = tg.request.environ.get('identity')
    if identity:
        csrf_token = identity.get('_csrf_token', None)
        if csrf_token:
            new_url = update_qs(new_url, {'_csrf_token': csrf_token},
                    overwrite=True)
    return new_url

def add_fas_auth_middleware(self, app, *args):
    ''' Add our FAS authentication middleware.

    This is a convenience method that sets up the FAS authentication
    middleware.  It needs to be used in :file:`app/config/app_cfg.py` like
    this:

    .. code-block:: diff

         from myapp import model
         from myapp.lib import app_globals, helpers.

        -base_config = AppConfig()
        +from fedora.tg.tg2utils import add_fas_auth_middleware
        +
        +class MyAppConfig(AppConfig):
        +    add_auth_middleware = add_fas_auth_middleware
        +
        +base_config = MyAppConfig()
        +
         base_config.renderers = []

         base_config.package = myapp

    The configuration of the faswho middleware is done via attributes on
    MyAppConfig.  For instance, to change the base url for the FAS server to
    be authenticated against, set the connection to insecure for testing, and
    the url of the login form, do this::

        from bunch import Bunch
        class MyAppConfig(AppConfig):
            fas_auth = Bunch(
                    fas_url='https://fakefas.fedoraproject.org/accounts', 
                    insecure=True, login_form_url='/alternate/login')
            add_auth_middleware = add_fas_auth_middleware

    The complete set of values that can be set in :attr:`fas_auth` is the same
    as the parameters that can be passed to
    :func:`fedora.wsgi.faswho.faswhoplugin.make_faswho_middleware`
    '''
    # Set up csrf protection
    enable_csrf()

    booleanize_predicates()

    if not hasattr(self, 'fas_auth'):
        self.fas_auth = Bunch()

    # Configuring auth logging:
    if 'log_stream' not in self.fas_auth:
        self.fas_auth['log_stream'] = logging.getLogger('auth')

    # Pull in some of the default auth arguments
    auth_args = copy(self.fas_auth)

    app = make_faswho_middleware(app, **auth_args)
    return app


def enable_csrf():
    '''A startup function to setup :ref:`CSRF-Protection`.

    This should be run at application startup.  It does three things:

    1) overrides the :func:`tg.url` function with
       :func:`fedora.tg.tg2utils.url` so that :term:`CSRF` tokens are
       appended to URLs.
    2) tells the TG2 app to ignore `_csrf_token`.  This lets the app know not
       to throw an error if the variable is passed through to the app.
    3) adds :func:`fedora.tg.fedora_template` function to the template
       variables.  This lets us xi:include templates from python-fedora in
       our templates.

    Presently, this is run when the faswho middleware is invoked.  See the
    documentation for :func:`fedora.tg.tgutils.add_fas_auth_middleware` for
    how to enable that.

    .. note::

        The following code is broken at least as late as
        :term:`TurboGears`-2.0.3.  We need to have something similar in order
        to use CSRF protection with applications that do not always want to
        rely on FAS to authenticate.

        .. seealso:: http://trac.turbogears.org/ticket/2432

        To run this at application startup, add
        code like the following to :file:`MYAPP/config/app_config.py`::

        from fedora.tg.tg2utils import enable_csrf
        base_config.call_on_startup = [enable_csrf]

    If we can get the :ref:`CSRF-Protection` into upstream :term:`TurboGears`,
    we might be able to remove this in the future.

    .. versionadded:: 0.3.17
       Added to enable :ref:`CSRF-Protection`
    '''
    # Override the tg.url function with our own
    tg.url = url
    tg.controllers.url = url
    tg.controllers.util.url = url

    # Ignore the _csrf_token parameter
    ignore = config.get('ignore_parameters', [])
    if '_csrf_token' not in ignore:
        ignore.append('_csrf_token')
        config['ignore_parameters'] = ignore

    # Add a function to the template tg stdvars that looks up a template.
    var_provider = config.get('variable_provider', None)
    if var_provider:
        config['variable_provider'] = lambda: \
            var_provider().update({'fedora_template': fedora_template})
    else:
        config['variable_provider'] = lambda: {'fedora_template':
                fedora_template}
__all__ = ('enable_csrf', 'fedora_template', 'tg_url', 'url')
