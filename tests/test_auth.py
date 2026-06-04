"""Unit tests for openedx_rest_api_client.auth."""

import requests

from openedx_rest_api_client.auth import BearerAuth, SuppliedJwtAuth


def _prepared_request():
    return requests.Request("GET", "http://example.com/").prepare()


def _apply(auth):
    """Run the auth callable against a fresh request and return its headers."""
    return auth(_prepared_request()).headers


def test_supplied_jwt_auth_sets_jwt_authorization_header():
    headers = _apply(SuppliedJwtAuth("the-token"))
    assert headers["Authorization"] == "JWT the-token"


def test_supplied_jwt_auth_stores_token():
    auth = SuppliedJwtAuth("the-token")
    assert auth.token == "the-token"


def test_bearer_auth_sets_bearer_authorization_header():
    headers = _apply(BearerAuth("the-token"))
    assert headers["Authorization"] == "Bearer the-token"


def test_bearer_auth_stores_token():
    auth = BearerAuth("the-token")
    assert auth.token == "the-token"


def test_auth_returns_same_request_object():
    request = _prepared_request()
    auth = BearerAuth("x")
    assert auth(request) is request


def test_token_is_mutable_after_construction():
    """The session swaps the token in after authenticating, so it must be writable."""
    auth = BearerAuth(None)
    auth.token = "later-token"
    headers = _apply(auth)
    assert headers["Authorization"] == "Bearer later-token"
