# -*- coding: utf-8 -*-
""" Test the OpenIDCClient. """


import shutil
import tempfile
import unittest
from mock import MagicMock, patch

import fedora.client.openidcclient as openidcclient

BASE_URL = 'http://app/'
IDP_URL = 'https://idp/'


def set_token(client, toreturn):
    """Mock helper for _get_server to set a retrieved token."""
    def setter(app):
        client._retrieved_code = toreturn
        return MagicMock()
    return setter


def mock_request(responses):
    """Mock helper for responding to HTTP requests."""
    def perform(method, url, **extra):
        def rfs(toret):
            """Helper for Raise For Status."""
            def call():
                if toret.status_code != 200:
                    raise Exception('Mocked response %s' % toret.status_code)
            return call

        toreturn = MagicMock()
        if url in responses:
            if len(responses[url]) == 0:
                raise Exception('Unhandled requested to %s (extra %s)' %
                                (url, extra))
            retval = responses[url][0]
            responses[url] = responses[url][1:]
            toreturn.status_code = 200
            if '_code' in retval:
                toreturn.status_code = retval['_code']
                del retval['_code']
            toreturn.json = MagicMock(return_value=retval)
            toreturn.raise_for_status = rfs(toreturn)
            return toreturn
        else:
            raise Exception('Unhandled mocked URL: %s (extra: %s)' %
                            (url, extra))
    return perform


class OpenIdBaseClientTest(unittest.TestCase):

    """Test the OpenId Base Client."""

    def setUp(self):
        self.cachedir = tempfile.mkdtemp('oidcclient')
        openidcclient.webbrowser = MagicMock()
        self.client = openidcclient.OpenIDCBaseClient(
            BASE_URL,
            'myapp',
            id_provider=IDP_URL,
            cachedir=self.cachedir)

    def tearDown(self):
        shutil.rmtree(self.cachedir)

    def test_cachefile(self):
        """Test that the cachefile name is set by app id."""
        with self.client._cache_lock:
            self.assertEqual('oidc_myapp.json',
                             self.client._cachefile.rsplit('/', 1)[1])

    def test_get_new_token_cancel(self):
        """Test that we handle it correctly if the user cancels."""
        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, False)) as gsmock:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request({})) as postmock:
                result = self.client._get_new_token(
                    ['test_get_new_token_cancel'])
                self.assertEqual(result, None)
                gsmock.assert_called_once()
                postmock.assert_not_called()

    def test_get_new_token_error(self):
        """Test that we handle errors correctly."""
        postresp = {'https://idp/Token': [
                    {'error': 'some_error',
                     'error_description': 'Some error occured'}]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                result = self.client._get_new_token(
                    ['test_get_new_token_error'])
                self.assertEqual(result, None)
                gsm.assert_called_once()
                postmock.assert_called_once_with(
                    'POST',
                    'https://idp/Token',
                    data={'code': 'authz',
                          'client_secret': 'notsecret',
                          'grant_type': 'authorization_code',
                          'client_id': 'python-fedora',
                          'redirect_uri': 'http://localhost:1/'})

    def test_get_new_token_working(self):
        """Test for a completely succesful case."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'}]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                result = self.client._get_new_token(
                    ['test_get_new_token_working'])
                self.assertNotEqual(result, None)
                gsm.assert_called_once()
                postmock.assert_called_once_with(
                    'POST',
                    'https://idp/Token',
                    data={'code': 'authz',
                          'client_secret': 'notsecret',
                          'grant_type': 'authorization_code',
                          'client_id': 'python-fedora',
                          'redirect_uri': 'http://localhost:1/'})

    def test_get_token_no_new(self):
        """Test that if we don't have a token we can skip getting a new oen."""
        self.assertEqual(self.client.get_token(['test_get_token_no_new'],
                                               new_token=False),
                         None)

    def test_get_token_from_cache(self):
        """Test that if we have a cached token, that gets returned."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'}]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                result = self.client._get_new_token(
                    ['test_get_token_from_cache'])
                self.assertNotEqual(result, None)
                gsm.assert_called_once()
                postmock.assert_called_once_with(
                    'POST',
                    'https://idp/Token',
                    data={'code': 'authz',
                          'client_secret': 'notsecret',
                          'grant_type': 'authorization_code',
                          'client_id': 'python-fedora',
                          'redirect_uri': 'http://localhost:1/'})

        self.assertNotEqual(
            self.client.get_token(['test_get_token_from_cache'],
                                  new_token=False),
            None)

    def test_get_token_new(self):
        """Test that get_token can get a new token."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'}]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                self.assertNotEqual(
                    self.client.get_token(['test_get_token_new'],
                                          new_token=True),
                    None)
                gsm.assert_called_once()
                postmock.assert_called_once_with(
                    'POST',
                    'https://idp/Token',
                    data={'code': 'authz',
                          'client_secret': 'notsecret',
                          'grant_type': 'authorization_code',
                          'client_id': 'python-fedora',
                          'redirect_uri': 'http://localhost:1/'})

    def test_report_token_issue_refreshable(self):
        """Test that we refresh a token if problems are reported."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'},
                    {'access_token': 'refreshedtoken',
                     'refresh_token': 'refreshtoken2',
                     'expires_in': 600,
                     'token_type': 'Bearer'}]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                self.assertNotEqual(
                    self.client.get_token(
                        ['test_report_token_issue_refreshable'],
                        new_token=True),
                    None)
                gsm.assert_called_once()
                postmock.assert_called_with(
                    'POST',
                    'https://idp/Token',
                    data={'code': 'authz',
                          'client_secret': 'notsecret',
                          'grant_type': 'authorization_code',
                          'client_id': 'python-fedora',
                          'redirect_uri': 'http://localhost:1/'})
                postmock.reset_mock()
                self.assertNotEqual(self.client.report_token_issue(),
                                    None)
                postmock.assert_called_once_with(
                    'POST',
                    'https://idp/Token',
                    data={'client_id': 'python-fedora',
                          'client_secret': 'notsecret',
                          'grant_type': 'refresh_token',
                          'refresh_token': 'refreshtoken'})

    def test_report_token_issue_revoked(self):
        """Test that we only try to refresh once."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'},
                    {'error': 'invalid_token',
                     'error_description': 'This token is not valid'}]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                self.assertNotEqual(
                    self.client.get_token(
                        ['test_report_token_issue_revoked'],
                        new_token=True),
                    None)
                gsm.assert_called_once()
                postmock.assert_called_with(
                    'POST',
                    'https://idp/Token',
                    data={'code': 'authz',
                          'client_secret': 'notsecret',
                          'grant_type': 'authorization_code',
                          'client_id': 'python-fedora',
                          'redirect_uri': 'http://localhost:1/'})
                postmock.reset_mock()
                self.assertEqual(self.client.report_token_issue(),
                                 None)
                postmock.assert_called_once_with(
                    'POST',
                    'https://idp/Token',
                    data={'client_id': 'python-fedora',
                          'client_secret': 'notsecret',
                          'grant_type': 'refresh_token',
                          'refresh_token': 'refreshtoken'})

    def test_send_request_valid_token(self):
        """Test that we send the token."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'}],
                    'http://app/test': [
                     {}
                    ]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                result = self.client.send_request(
                    'test',
                    scopes=['test_send_request_valid_token'])
                gsm.assert_called_once()
                self.assertEqual(result.json(), {})
                postmock.assert_called_with(
                    'POST',
                    'http://app/test',
                    headers={'Authorization': 'Bearer testtoken'})

    def test_send_request_not_valid_token_500(self):
        """Test that we don't refresh if we get a server error."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'}],
                    'http://app/test': [
                     {'_code': 500},
                    ]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                result = self.client.send_request(
                    'test',
                    scopes=['test_send_request_not_valid_token_500'])
                gsm.assert_called_once()
                self.assertEqual(result.status_code, 500)
                self.assertEqual(result.json(), {})
                postmock.assert_called_with(
                    'POST',
                    'http://app/test',
                    headers={'Authorization': 'Bearer testtoken'})

    def test_send_request_not_valid_token_403(self):
        """Test that we don't refresh if the app returns a 403 (forbidden)"""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'}],
                    'http://app/test': [
                     {'_code': 403},
                    ]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                result = self.client.send_request(
                    'test',
                    scopes=['test_send_request_not_valid_token_403'])
                gsm.assert_called_once()
                self.assertEqual(result.status_code, 403)
                self.assertEqual(result.json(), {})
                postmock.assert_called_with(
                    'POST',
                    'http://app/test',
                    headers={'Authorization': 'Bearer testtoken'})

    def test_send_request_not_valid_token_401_refreshable(self):
        """Test that we do refresh with a 401."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'},
                    {'access_token': 'refreshedtoken',
                     'refresh_token': 'refreshtoken2',
                     'expires_in': 600,
                     'token_type': 'Bearer'}],
                    'http://app/test': [
                     {'_code': 401},
                     {}
                    ]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)) as postmock:
                result = self.client.send_request(
                    'test',
                    scopes=['test_send_request_not_valid_token_401_' +
                            'refreshable'],
                    json={'foo': 'bar'})
                gsm.assert_called_once()
                self.assertEqual(result.json(), {})
                postmock.assert_called_with(
                    'POST',
                    'http://app/test',
                    json={'foo': 'bar'},
                    headers={'Authorization': 'Bearer refreshedtoken'})

    def test_send_request_not_valid_token_401_not_refreshable(self):
        """Test that we only try to refresh once and then throw away."""
        postresp = {'https://idp/Token': [
                    {'access_token': 'testtoken',
                     'refresh_token': 'refreshtoken',
                     'expires_in': 600,
                     'token_type': 'Bearer'},
                    {'error': 'invalid_token',
                     'error_description': 'Could not refresh'}],
                    'http://app/test': [
                     {'_code': 401},
                    ]}

        with patch.object(self.client, '_get_server',
                          side_effect=set_token(self.client, 'authz')) as gsm:
            with patch.object(openidcclient.requests, 'request',
                              side_effect=mock_request(postresp)):
                result = self.client.send_request(
                    'test',
                    scopes=['test_send_request_not_valid_token_401_not_' +
                            'refreshable'])
                gsm.assert_called_once()
                self.assertEqual(result.status_code, 401)
                self.assertEqual(result.json(), {})
                # Make sure that if there was an error, the token is cleared
                self.assertEqual(self.client.get_token(
                    ['test_send_request_not_valid_token_401_not_refreshable'],
                    new_token=False), None)
