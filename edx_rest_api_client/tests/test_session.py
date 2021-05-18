import datetime
import json
from unittest import mock, TestCase

import ddt
import requests
import responses

from freezegun import freeze_time

from edx_rest_api_client.session import OAuthAPISession
from edx_rest_api_client.tests.mixins import AuthenticationTestMixin

URL = 'http://example.com/api/v2'
OAUTH_URL = "http://test-auth.com/oauth2/access_token"
OAUTH_URL_2 = "http://test-auth.com/edx/oauth2/access_token"
SIGNING_KEY = 'edx'
USERNAME = 'edx'
FULL_NAME = 'édx äpp'
EMAIL = 'edx@example.com'
TRACKING_CONTEXT = {'foo': 'bar'}
ACCESS_TOKEN = 'abc123'
JWT = 'abc.123.doremi'


@ddt.ddt
class OAuthAPIClientTests(AuthenticationTestMixin, TestCase):
    """
    Tests for OAuthAPISession
    """
    base_url = 'http://testing.test'
    client_id = 'test'
    client_secret = 'secret'

    @responses.activate
    @ddt.data(
        ('http://testing.test', None, 'http://testing.test/oauth2/access_token'),
        ('http://testing.test', '/edx', 'http://testing.test/edx/oauth2/access_token'),
        ('http://testing.test', '/edx/oauth2', 'http://testing.test/edx/oauth2/access_token'),
        ('http://testing.test', '/edx/oauth2/access_token', 'http://testing.test/edx/oauth2/access_token'),
        ('http://testing.test/oauth2', None, 'http://testing.test/oauth2/access_token'),
        ('http://testing.test/test', '/edx/oauth2/access_token', 'http://testing.test/test/edx/oauth2/access_token'),
    )
    @ddt.unpack
    def test_automatic_auth(self, client_base_url, custom_oauth_uri, expected_oauth_url):
        """
        Test that the JWT token is automatically set
        """
        client_session = OAuthAPISession(client_base_url, self.client_id, self.client_secret)
        client_session.oauth_uri = custom_oauth_uri

        self._mock_auth_api(expected_oauth_url, 200, {'access_token': 'abcd', 'expires_in': 60})
        self._mock_auth_api(self.base_url + '/endpoint', 200, {'status': 'ok'})
        response = client_session.post(self.base_url + '/endpoint', data={'test': 'ok'})
        self.assertIn('client_id=%s' % self.client_id, responses.calls[0].request.body)
        self.assertEqual(client_session.auth.token, 'abcd')
        self.assertEqual(response.json()['status'], 'ok')

    @responses.activate
    def test_automatic_token_refresh(self):
        """
        Test that the JWT token is automatically refreshed
        """
        tokens = ['cred2', 'cred1']

        def auth_callback(request):
            resp = {'expires_in': 60}
            if 'grant_type=client_credentials' in request.body:
                resp['access_token'] = tokens.pop()
            return 200, {}, json.dumps(resp)

        responses.add_callback(
            responses.POST, self.base_url + '/oauth2/access_token',
            callback=auth_callback,
            content_type='application/json',
        )

        client_session = OAuthAPISession(self.base_url, self.client_id, self.client_secret)
        self._mock_auth_api(self.base_url + '/endpoint', 200, {'status': 'ok'})
        response = client_session.post(self.base_url + '/endpoint', data={'test': 'ok'})
        first_call_datetime = datetime.datetime.utcnow()
        self.assertEqual(client_session.auth.token, 'cred1')
        self.assertEqual(response.json()['status'], 'ok')
        # after only 30 seconds should still use the cached token
        with freeze_time(first_call_datetime + datetime.timedelta(seconds=30)):
            response = client_session.post(self.base_url + '/endpoint', data={'test': 'ok'})
            self.assertEqual(client_session.auth.token, 'cred1')
        # after just under a minute, should request a new token
        # - expires early due to ACCESS_TOKEN_EXPIRED_THRESHOLD_SECONDS
        with freeze_time(first_call_datetime + datetime.timedelta(seconds=56)):
            response = client_session.post(self.base_url + '/endpoint', data={'test': 'ok'})
            self.assertEqual(client_session.auth.token, 'cred2')

    @mock.patch('edx_rest_api_client.session.requests.post')
    def test_access_token_request_timeout_wiring2(self, mock_access_token_post):
        mock_access_token_post.return_value.json.return_value = {'access_token': 'token', 'expires_in': 1000}

        timeout_override = (6.1, 2)
        client = OAuthAPISession(self.base_url, self.client_id, self.client_secret, timeout=timeout_override)
        client._ensure_authentication()  # pylint: disable=protected-access

        assert mock_access_token_post.call_args.kwargs['timeout'] == timeout_override

    @responses.activate
    def test_access_token_invalid_json_response(self):
        responses.add(responses.POST,
                      self.base_url + '/oauth2/access_token',
                      status=200,
                      body="Not JSON")
        client = OAuthAPISession(self.base_url, self.client_id, self.client_secret)

        with self.assertRaises(requests.RequestException):
            client._ensure_authentication()  # pylint: disable=protected-access

    @responses.activate
    def test_access_token_bad_response_code(self):
        responses.add(responses.POST,
                      self.base_url + '/oauth2/access_token',
                      status=500,
                      json={})
        client = OAuthAPISession(self.base_url, self.client_id, self.client_secret)
        with self.assertRaises(requests.HTTPError):
            client._ensure_authentication()  # pylint: disable=protected-access

    @responses.activate
    def test_get_jwt_access_token(self):
        token = 'abcd'
        self._mock_auth_api(self.base_url + '/oauth2/access_token', 200, {'access_token': token, 'expires_in': 60})
        client = OAuthAPISession(self.base_url, self.client_id, self.client_secret)
        access_token = client.get_jwt_access_token()
        self.assertEqual(access_token, token)
