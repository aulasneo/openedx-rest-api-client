import datetime
from unittest import TestCase

# import jwt
import requests
import responses

from openedx_rest_api_client import auth

CURRENT_TIME = datetime.datetime(2015, 7, 2, 10, 10, 10)


class BearerAuthTests(TestCase):
    def setUp(self):
        super().setUp()
        self.url = 'http://example.com/'
        responses.add(responses.GET, self.url)

    @responses.activate
    def test_headers(self):
        """ Verify the class adds an Authorization headers with the bearer token. """
        token = 'abc123'
        requests.get(self.url, auth=auth.BearerAuth(token))
        self.assertEqual(responses.calls[0].request.headers['Authorization'], f'Bearer {token}')


class SuppliedJwtAuthTests(TestCase):
    signing_key = 'super-secret'
    url = 'http://example.com/'

    def setUp(self):
        """Set up tests."""
        super().setUp()
        responses.add(responses.GET, self.url)

    @responses.activate
    def test_headers(self):
        """Verify that the token is added to the Authorization headers."""
        # payload = {
        #     'key1': 'value1',
        #     'key2': 'vαlue2'
        # }
        # token = jwt.encode(payload, self.signing_key)

        # The key bellow is created by the commands commented above. We do this to avoid having to import pyjwt

        # pylint: disable=line-too-long
        token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJrZXkxIjoidmFsdWUxIiwia2V5MiI6InZcdTAzYjFsdWUyIn0.DxmqDCAnDlDRWmkqqWIUeGiRPeW7DacUPxvS6x9lZb4'
        requests.get(self.url, auth=auth.SuppliedJwtAuth(token))
        self.assertEqual(responses.calls[0].request.headers['Authorization'], f'JWT {token}')
