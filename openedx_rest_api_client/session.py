import os
import socket

import requests
import requests.utils

from openedx_rest_api_client.auth import SuppliedJwtAuth, BearerAuth
from openedx_rest_api_client.cached_token import CachedToken

from openedx_rest_api_client.__version__ import __version__

# How long should we wait to connect to the auth service.
# https://requests.readthedocs.io/en/master/user/advanced/#timeouts
REQUEST_CONNECT_TIMEOUT = 3.05
REQUEST_READ_TIMEOUT = 5


def user_agent():
    """
    Return a User-Agent that identifies this client.

    Example:
        python-requests/2.9.1 edx-rest-api-client/1.7.2 ecommerce

    The last item in the list will be the application name, taken from the
    OS environment variable EDX_REST_API_CLIENT_NAME. If that environment
    variable is not set, it will default to the hostname.
    """
    client_name = 'unknown_client_name'
    try:
        client_name = os.environ.get("EDX_REST_API_CLIENT_NAME") or socket.gethostbyname(socket.gethostname())
    except:  # pylint: disable=bare-except
        pass  # using 'unknown_client_name' is good enough.  no need to log.
    return "{} edx-rest-api-client/{} {}".format(
        requests.utils.default_user_agent(),  # e.g. "python-requests/2.9.1"
        __version__,  # version of this client
        client_name
    )


USER_AGENT = user_agent()


class OAuthAPISession(requests.Session):
    """
    A :class:`requests.Session` that automatically authenticates against edX's preferred
    authentication method, given a client id and client secret. The underlying implementation
    is subject to change.

    Usage example::

        session = OAuthAPISession(
            settings.BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL,
            settings.BACKEND_SERVICE_EDX_OAUTH2_KEY,
            settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET,
        )
        response = session.get(
            settings.EXAMPLE_API_SERVICE_URL + 'example/',
            params={'username': user.username},
            timeout=(3.1, 0.5), # Always set a timeout.
        )
        response.raise_for_status()  # could be an error response
        response_data = response.json()

    For more usage details, see documentation of the :class:`requests.Session` object:
    - https://requests.readthedocs.io/en/master/user/advanced/#session-objects

    """

    # If the oauth_uri is set, it will be appended to the base_url.
    # Also, if oauth_uri does not end with `/oauth2/access_token`, it will be adjusted as necessary to do so.
    # This was needed when using the client to connect with a third-party (rather than LMS).
    oauth_uri = None

    def __init__(self,
                 base_url: str,
                 client_id: str,
                 client_secret: str,
                 timeout: (float, float) = (REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT),
                 bearer: bool = False,
                 **kwargs) -> None:
        """
        Args:
            base_url (str): base url of the LMS oauth endpoint, which can optionally include the path `/oauth2`.
                Commonly example settings that would work for `base_url` might include:
                    LMS_BASE_URL = 'http://edx.devstack.lms:18000'
                    BACKEND_SERVICE_EDX_OAUTH2_PROVIDER_URL = 'http://edx.devstack.lms:18000/oauth2'
            client_id (str): Client ID
            client_secret (str): Client secret
            timeout (tuple(float,float)): Requests timeout parameter for access token requests.
                (https://requests.readthedocs.io/en/master/user/advanced/#timeouts)

        """
        super().__init__(**kwargs)
        self.headers['user-agent'] = USER_AGENT
        self.headers['Content-Type'] = "application/JSON"

        if bearer:
            self.auth = BearerAuth(None)
            self._token_type = 'bearer'
        else:
            self.auth = SuppliedJwtAuth(None)
            self._token_type = 'jwt'

        self._base_url = base_url.rstrip('/')
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout

        self._access_token = None

    def get_base_url(self) -> str:
        return self._base_url

    def _ensure_authentication(self) -> None:
        """
        Ensures that the Session's auth.token is set with an unexpired token.

        Raises:
            requests.RequestException if there is a problem retrieving the access token.

        """

        if not self._access_token:
            oauth_url = self._base_url if not self.oauth_uri else self._base_url + self.oauth_uri

            self._access_token = CachedToken(
                oauth_url,
                self._client_id,
                self._client_secret,
                grant_type='client_credentials',
                user_agent=USER_AGENT,
                timeout=self._timeout,
                token_type=self._token_type
            )

        oauth_access_token_response = self._access_token.get_and_cache_oauth_access_token()

        self.auth.token, _ = oauth_access_token_response

    def get_jwt_access_token(self):
        """
        Returns the JWT access token that will be used to make authenticated calls.

        The intention of this method is only to allow you to decode the JWT if you require
        any of its details, like the username. You should not use the JWT to make calls by
        another client.

        Here is example code that properly uses the configured JWT decoder:
        https://github.com/edx/edx-drf-extensions/blob/master/edx_rest_framework_extensions/auth/jwt/authentication.py#L180-L190
        """
        self._ensure_authentication()
        return self.auth.token

    def request(self, method, url, **kwargs):  # pylint: disable=arguments-differ
        """
        Overrides Session.request to ensure that the session is authenticated.

        Note: Typically, users of the client won't call this directly, but will
        instead use Session.get or Session.post.

        """
        self._ensure_authentication()
        return super().request(method, url, **kwargs)
