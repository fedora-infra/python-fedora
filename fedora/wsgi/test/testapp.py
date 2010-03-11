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
"""
:mod:`fedora.wsgi.test` - Test infrastructure for python-fedora WSGI middleware
===============================================================================

This module contains a :meth:`make_app` method that resides on the
`paste.app_factory` entry-point.  This sets up a fake TurboGears2 application
with various pieces of middleware.

.. moduleauthor:: Luke Macken <lmacken@redhat.com>
"""

import os
from tg import config
from paste.script.appinstall import SetupCommand

def make_app(global_conf, **kw):
    from fedora.wsgi.test.config import base_config
    load_environment = base_config.make_load_environment()
    make_base_app = base_config.setup_tg_wsgi_app(load_environment)
    app = make_base_app(global_conf, **kw)

    if config.get('use_csrf'):
        from fedora.wsgi.csrf import CSRFProtectionMiddleware
        app = CSRFProtectionMiddleware(app)
    if config.get('use_faswho'):
        from fedora.wsgi.faswho import make_faswho_middleware
        app = make_faswho_middleware(app)

    return app
