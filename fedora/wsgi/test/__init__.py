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

import os
try:
    import simplejson as json
except ImportError:
    import json

from tg import config as tg_config
from paste.deploy import loadapp
from paste.script.appinstall import SetupCommand
from webtest import TestApp
from nose.tools import eq_
from fedora.wsgi.test import model
from fedora.wsgi.test.testapp import make_app

__all__ = ['make_app', 'TestTG2App', 'setup_db', 'teardown_db']

def setup_db():
    """Method used to build a database"""
    engine = tg_config['pylons.app_globals'].sa_engine
    model.init_model(engine)
    model.metadata.create_all(engine)

def teardown_db():
    """Method used to destroy a database"""
    engine = tg_config['pylons.app_globals'].sa_engine
    model.metadata.drop_all(engine)

class TestTG2App(object):
    application_under_test = 'main'

    def setUp(self):
        wsgiapp = loadapp('config:test.ini#%s' % self.application_under_test,
                          relative_to='.')
        self.app = TestApp(wsgiapp)

        # Setting it up:
        test_file = os.path.abspath('test.ini')
        cmd = SetupCommand('setup-app')
        cmd.run([test_file])

    def tearDown(self):
        """Method called by nose after running each test"""
        # Cleaning up the database:
        teardown_db()

    def test_tg2_app(self):
        """ Ensure our dummy TG2 app actually works """
        eq_(json.loads(self.app.get('/').body), {'foo': 'bar'})
