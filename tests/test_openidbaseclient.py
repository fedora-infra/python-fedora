#!/usr/bin/python2 -tt
# -*- coding: utf-8 -*-

""" Test the OpenIdBaseClient. """


import os
import shutil
import tempfile
import unittest
import functools

from nose.exc import SkipTest

from fedora.client.baseclient import OpenIdBaseClient

BASE_URL = 'http://127.0.0.1:5000'
BASE_URL = 'http://209.132.184.188'
LOGIN_URL = '{}/login/'.format(BASE_URL)

try:
    from nose.tools.nontrivial import make_decorator
except ImportError:
    # It lives here in older versions of nose (el6)
    from nose.tools import make_decorator


def dev_only(func):
    """A decorator that skips tests if they are not run by a developer.

    This decorator allows us to have tests that a developer might want to
    run but shouldn't be run by random people building the package.  It
    also makes non-networked build systems happy.

    """
    @functools.wraps(func)
    def newfunc(self, *args, **kw):
        if not os.environ.get('DEVELOPER_TESTS', None):
            raise SkipTest('Only run if you are a python-fedora developer')
        return func(self, *args, **kw)
    return make_decorator(func)(newfunc)


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

    @dev_only
    def test_no_openid_session(self):
        """Raise AuthError for no session on service or openid server."""
        self.assertRaises(AuthError, self.client.login)

    @dev_only
    def test_no_service_session(self):
        """Open a service session when we have an openid session."""
        pass
