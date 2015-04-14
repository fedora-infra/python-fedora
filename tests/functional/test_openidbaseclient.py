# -*- coding: utf-8 -*-
""" Test the OpenIdBaseClient. """


import os
import shutil
import tempfile
import unittest

from .functional_test_utils import networked

from fedora.client import FedoraServiceError
from fedora.client.openidbaseclient import OpenIdBaseClient

BASE_URL = 'http://127.0.0.1:5000'
BASE_URL = 'http://209.132.184.188'
LOGIN_URL = '{}/login/'.format(BASE_URL)

class OpenIdBaseClientTest(unittest.TestCase):

    """Test the OpenId Base Client."""

    def setUp(self):
        self.client = OpenIdBaseClient(BASE_URL)
        self.session_file = os.path.expanduser(
            '~/.fedora/baseclient-sessions.sqlite')
        try:
            self.backup_dir = tempfile.mkdtemp(dir='~/.fedora/')
        except OSError:
            self.backup_dir = tempfile.mkdtemp()

        self.saved_session_file = os.path.join(
            self.backup_dir, 'baseclient-sessions.sqlite.bak')
        self.clear_cookies()

    def tearDown(self):
        self.restore_cookies()
        shutil.rmtree(self.backup_dir)

    def clear_cookies(self):
        try:
            shutil.move(self.session_file, self.saved_session_file)
        except IOError as e:
            # No previous sessionfile is fine
            if e.errno != 2:
                raise
            # Sentinel to say that there was no previous session_file
            self.saved_session_file = None

    def restore_cookies(self):
        if self.saved_session_file:
            shutil.move(self.saved_session_file, self.session_file)

    @networked
    def test_no_openid_session(self):
        """Raise FedoraServiceError for no session on service or openid server."""
        self.assertRaises(FedoraServiceError, self.client.login, 'username', 'password')

    @networked
    def test_no_service_session(self):
        """Open a service session when we have an openid session."""
        pass
