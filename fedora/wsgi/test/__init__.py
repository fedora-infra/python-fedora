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

import sys
import simplejson

from os import path
from tg import config
from paste.deploy import loadapp
from paste.script.appinstall import SetupCommand
from routes import url_for
from webtest import TestApp
from nose.tools import eq_
from testapp import *

class TestTG2App(object):
    application_under_test = 'main'

    def setUp(self):
        wsgiapp = loadapp('config:test.ini#%s' % self.application_under_test,
                          relative_to='.')
        self.app = TestApp(wsgiapp)

    def test_tg2_app(self):
        """ Ensure our dummy TG2 app actually works """
        eq_(simplejson.loads(self.app.get('/').body), {'foo': 'bar'})


class TestCSRF(TestTG2App):
    application_under_test = 'main_with_csrf'

    def test_wsgi_app(self):
        resp = self.app.get('/')
        assert resp
