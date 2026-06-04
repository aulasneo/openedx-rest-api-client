"""Unit tests for openedx_rest_api_client.session."""

import os
from unittest import mock

import responses

from openedx_rest_api_client import session as session_module
from openedx_rest_api_client.auth import BearerAuth, SuppliedJwtAuth
from openedx_rest_api_client.session import OAuthAPISession, user_agent


def _add_token_response(token="tok-1"):
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": token, "expires_in": 3600},
        status=200,
    )


# --- user_agent -------------------------------------------------------------

def test_user_agent_uses_env_var_for_client_name():
    with mock.patch.dict(os.environ, {"EDX_REST_API_CLIENT_NAME": "my-service"}):
        ua = user_agent()
    assert ua.endswith("my-service")
    assert "edx-rest-api-client/" in ua


def test_user_agent_falls_back_when_env_missing():
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch.object(
            session_module.socket, "gethostbyname", side_effect=OSError,
        ):
            ua = user_agent()
    assert ua.endswith("unknown_client_name")


# --- OAuthAPISession construction ------------------------------------------

def test_session_defaults_to_jwt_auth():
    sess = OAuthAPISession("http://lms:18000", "id", "secret", bearer=False)
    assert isinstance(sess.auth, SuppliedJwtAuth)
    assert sess._token_type == "jwt"


def test_session_uses_bearer_auth_when_requested():
    sess = OAuthAPISession("http://lms:18000", "id", "secret", bearer=True)
    assert isinstance(sess.auth, BearerAuth)
    assert sess._token_type == "bearer"


def test_session_strips_trailing_slash_from_base_url():
    sess = OAuthAPISession("http://lms:18000/", "id", "secret")
    assert sess.get_base_url() == "http://lms:18000"


def test_session_sets_user_agent_header():
    sess = OAuthAPISession("http://lms:18000", "id", "secret")
    assert sess.headers["user-agent"] == session_module.USER_AGENT


# --- authentication flow ----------------------------------------------------

@responses.activate
def test_ensure_authentication_populates_auth_token():
    _add_token_response("tok-1")
    sess = OAuthAPISession("http://lms:18000", "id", "secret", bearer=True)

    sess._ensure_authentication()

    assert sess.auth.token == "tok-1"


@responses.activate
def test_get_jwt_access_token_returns_token():
    _add_token_response("jwt-tok")
    sess = OAuthAPISession("http://lms:18000", "id", "secret", bearer=False)

    assert sess.get_jwt_access_token() == "jwt-tok"


@responses.activate
def test_request_authenticates_before_calling_endpoint():
    _add_token_response("tok-1")
    responses.add(
        responses.GET,
        "http://lms:18000/api/example/",
        json={"ok": True},
        status=200,
    )

    sess = OAuthAPISession("http://lms:18000", "id", "secret", bearer=True)
    response = sess.get("http://lms:18000/api/example/")

    assert response.json() == {"ok": True}
    # The bearer token obtained during auth is attached to the API call.
    assert responses.calls[1].request.headers["Authorization"] == "Bearer tok-1"


@responses.activate
def test_oauth_uri_is_appended_to_base_url():
    responses.add(
        responses.POST,
        "http://lms:18000/custom/oauth2/access_token",
        json={"access_token": "tok-1", "expires_in": 3600},
        status=200,
    )

    sess = OAuthAPISession("http://lms:18000", "id", "secret", bearer=True)
    sess.oauth_uri = "/custom/oauth2"
    sess._ensure_authentication()

    assert sess.auth.token == "tok-1"
    assert responses.calls[0].request.url == "http://lms:18000/custom/oauth2/access_token"
