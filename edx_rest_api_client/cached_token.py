import datetime
import json

import requests
import requests.utils

# How long should we wait to connect to the auth service.
# https://requests.readthedocs.io/en/master/user/advanced/#timeouts
REQUEST_CONNECT_TIMEOUT = 3.05
REQUEST_READ_TIMEOUT = 5

# When caching tokens, use this value to err on expiring tokens a little early so they are
# sure to be valid at the time they are used.
ACCESS_TOKEN_EXPIRED_THRESHOLD_SECONDS = 5


def _get_oauth_url(url):
    """
    Returns the complete url for the oauth2 endpoint.

    Args:
        url (str): base url of the LMS oauth endpoint, which can optionally include some or all of the path
            ``/oauth2/access_token``. Common example settings that would work for ``url`` would include:
                LMS_BASE_URL = 'http://edx.devstack.lms:18000'
                BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL = 'http://edx.devstack.lms:18000/oauth2'

    """
    stripped_url = url.rstrip('/')
    if stripped_url.endswith('/access_token'):
        return url

    if stripped_url.endswith('/oauth2'):
        return stripped_url + '/access_token'

    return stripped_url + '/oauth2/access_token'


def get_oauth_access_token(url: str, client_id: str, client_secret: str,
                           token_type: str = 'jwt',
                           grant_type: str = 'client_credentials',
                           refresh_token=None,
                           user_agent=None,
                           timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT)) -> (str, datetime.datetime):
    """ Retrieves OAuth 2.0 access token using the given grant type.

    Args:
        url (str): Oauth2 access token endpoint, optionally including part of the path.
        client_id (str): client ID
        client_secret (str): client secret
        token_type (str): Type of token to return. Options include bearer and jwt.
        grant_type (str): One of 'client_credentials' or 'refresh_token'
        refresh_token (str): The previous access token (for grant_type=refresh_token)
        user_agent (str): identifies the agent in the HTTP header
        timeout (tuple(float,float)): Requests timeout parameter for access token requests.
            (https://requests.readthedocs.io/en/master/user/advanced/#timeouts)

    Raises:
        requests.RequestException if there is a problem retrieving the access token.

    Returns:
        tuple: Tuple containing (access token string, expiration datetime).

    """
    now = datetime.datetime.utcnow()
    data = {
        'grant_type': grant_type,
        'client_id': client_id,
        'client_secret': client_secret,
        'token_type': token_type,
    }
    if refresh_token:
        data['refresh_token'] = refresh_token
    else:
        assert grant_type != 'refresh_token', "refresh_token parameter required"

    response = requests.post(
        _get_oauth_url(url),
        data=data,
        headers={
            'User-Agent': user_agent,
        },
        timeout=timeout
    )
    response.raise_for_status()  # Raise an exception for bad status codes.

    try:
        data = response.json()
        access_token = data['access_token']
        expires_in = data['expires_in']
    except (KeyError, json.decoder.JSONDecodeError) as json_error:
        raise requests.RequestException(response=response) from json_error

    expires_at = now + datetime.timedelta(seconds=expires_in)

    return access_token, expires_at


class CachedToken:

    def __init__(self, url, client_id, client_secret, token_type='jwt',
                 grant_type='client_credentials',
                 refresh_token=None,
                 user_agent=None,
                 timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT)):

        self.oauth_access_token = None
        self.expiration = datetime.datetime.utcnow()

        self.url = url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_type = token_type
        self.grant_type = grant_type
        self.refresh_token = refresh_token
        self.user_agent = user_agent
        self.timeout = timeout

    def get_and_cache_oauth_access_token(self):
        """ Retrieves a possibly cached OAuth 2.0 access token using the given grant type.

        See ``get_oauth_access_token`` for usage details.

        First retrieves the access token from the cache and ensures it has not expired. If
        the access token either wasn't found in the cache, or was expired, retrieves a new
        access token and caches it for the lifetime of the token.

        Note: Consider tokens to be expired ACCESS_TOKEN_EXPIRED_THRESHOLD_SECONDS early
        to ensure the token won't expire while it is in use.

        Returns:
            tuple: Tuple containing (access token string, expiration datetime).

        """
        oauth_url = _get_oauth_url(self.url)

        # Attempt to get an unexpired cached access token
        if self.oauth_access_token:
            # Double-check the token hasn't already expired as a safety net.
            adjusted_expiration = self.expiration - datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRED_THRESHOLD_SECONDS)
            if datetime.datetime.utcnow() < adjusted_expiration:
                return self.oauth_access_token, self.expiration

        # Get a new access token if no unexpired access token was found in the cache.
        oauth_access_token_response = get_oauth_access_token(
            oauth_url,
            self.client_id,
            self.client_secret,
            grant_type=self.grant_type,
            refresh_token=self.refresh_token,
            user_agent=self.user_agent,
            timeout=self.timeout,
            token_type=self.token_type
        )

        # Cache the new access token with an expiration matching the lifetime of the token.
        self.oauth_access_token, expiration = oauth_access_token_response
        self.expiration = expiration - (datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRED_THRESHOLD_SECONDS))

        return self.oauth_access_token, self.expiration
