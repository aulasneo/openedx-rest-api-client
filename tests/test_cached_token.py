"""Unit tests for openedx_rest_api_client.cached_token."""

import datetime

import pytest
import requests
import responses

from openedx_rest_api_client import cached_token
from openedx_rest_api_client.cached_token import (
    CachedToken,
    _get_oauth_url,
    get_oauth_access_token,
)


# --- _get_oauth_url ---------------------------------------------------------

@pytest.mark.parametrize("url, expected", [
    # Bare base url gets the full path appended.
    ("http://lms:18000", "http://lms:18000/oauth2/access_token"),
    ("http://lms:18000/", "http://lms:18000/oauth2/access_token"),
    # A url ending in /oauth2 only needs /access_token.
    ("http://lms:18000/oauth2", "http://lms:18000/oauth2/access_token"),
    ("http://lms:18000/oauth2/", "http://lms:18000/oauth2/access_token"),
    # An already-complete url is returned unchanged.
    ("http://lms:18000/oauth2/access_token", "http://lms:18000/oauth2/access_token"),
])
def test_get_oauth_url(url, expected):
    assert _get_oauth_url(url) == expected


# --- get_oauth_access_token -------------------------------------------------

@responses.activate
def test_get_oauth_access_token_returns_token_and_expiry():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "abc123", "expires_in": 3600},
        status=200,
    )

    before = datetime.datetime.utcnow()
    token, expires_at = get_oauth_access_token(
        "http://lms:18000", "id", "secret",
    )
    after = datetime.datetime.utcnow()

    assert token == "abc123"
    assert before + datetime.timedelta(seconds=3600) <= expires_at
    assert expires_at <= after + datetime.timedelta(seconds=3600)


@responses.activate
def test_get_oauth_access_token_sends_expected_payload():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "abc123", "expires_in": 3600},
        status=200,
    )

    get_oauth_access_token(
        "http://lms:18000", "the-id", "the-secret",
        token_type="bearer", user_agent="ua/1.0",
    )

    sent = responses.calls[0].request
    assert sent.body is not None
    body = dict(pair.split("=") for pair in sent.body.split("&"))
    assert body["grant_type"] == "client_credentials"
    assert body["client_id"] == "the-id"
    assert body["client_secret"] == "the-secret"
    assert body["token_type"] == "bearer"
    assert sent.headers["User-Agent"] == "ua/1.0"


@responses.activate
def test_get_oauth_access_token_raises_on_http_error():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        status=401,
    )

    with pytest.raises(requests.HTTPError):
        get_oauth_access_token("http://lms:18000", "id", "secret")


@responses.activate
def test_get_oauth_access_token_raises_when_token_missing():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"expires_in": 3600},  # no access_token key
        status=200,
    )

    with pytest.raises(requests.RequestException):
        get_oauth_access_token("http://lms:18000", "id", "secret")


def test_get_oauth_access_token_requires_refresh_token_for_refresh_grant():
    with pytest.raises(AssertionError):
        get_oauth_access_token(
            "http://lms:18000", "id", "secret", grant_type="refresh_token",
        )


@responses.activate
def test_get_oauth_access_token_includes_refresh_token_when_provided():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "abc123", "expires_in": 60},
        status=200,
    )

    get_oauth_access_token(
        "http://lms:18000", "id", "secret",
        grant_type="refresh_token", refresh_token="r-token",
    )

    body = dict(pair.split("=") for pair in responses.calls[0].request.body.split("&"))
    assert body["refresh_token"] == "r-token"


# --- CachedToken ------------------------------------------------------------

@responses.activate
def test_cached_token_fetches_on_first_call():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "tok-1", "expires_in": 3600},
        status=200,
    )

    cached = CachedToken("http://lms:18000", "id", "secret")
    token, _ = cached.get_and_cache_oauth_access_token()

    assert token == "tok-1"
    assert len(responses.calls) == 1


@responses.activate
def test_cached_token_reuses_unexpired_token():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "tok-1", "expires_in": 3600},
        status=200,
    )

    cached = CachedToken("http://lms:18000", "id", "secret")
    cached.get_and_cache_oauth_access_token()
    token, _ = cached.get_and_cache_oauth_access_token()

    assert token == "tok-1"
    # Only one network call despite two retrievals.
    assert len(responses.calls) == 1


@responses.activate
def test_cached_token_refetches_when_expired():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "tok-1", "expires_in": 3600},
        status=200,
    )
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "tok-2", "expires_in": 3600},
        status=200,
    )

    cached = CachedToken("http://lms:18000", "id", "secret")
    cached.get_and_cache_oauth_access_token()
    # Force the cached token to look expired.
    cached.expiration = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)

    token, _ = cached.get_and_cache_oauth_access_token()

    assert token == "tok-2"
    assert len(responses.calls) == 2


@responses.activate
def test_cached_token_applies_expiry_threshold():
    responses.add(
        responses.POST,
        "http://lms:18000/oauth2/access_token",
        json={"access_token": "tok-1", "expires_in": 3600},
        status=200,
    )

    cached = CachedToken("http://lms:18000", "id", "secret")
    before = datetime.datetime.utcnow()
    _, expiration = cached.get_and_cache_oauth_access_token()

    # Cached expiration is pulled in by the early-expiry threshold.
    raw_expiry = before + datetime.timedelta(seconds=3600)
    threshold = datetime.timedelta(
        seconds=cached_token.ACCESS_TOKEN_EXPIRED_THRESHOLD_SECONDS,
    )
    assert expiration <= raw_expiry - threshold + datetime.timedelta(seconds=1)
