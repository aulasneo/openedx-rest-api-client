"""Unit tests for openedx_rest_api_client.client."""

import pytest
import requests
import responses

from openedx_rest_api_client.client import OpenedxRESTAPIClient

BASE_URL = "http://lms:18000"
TOKEN_URL = BASE_URL + "/oauth2/access_token"


def _add_token_response():
    responses.add(
        responses.POST,
        TOKEN_URL,
        json={"access_token": "tok-1", "expires_in": 3600},
        status=200,
    )


@pytest.fixture
def client():
    return OpenedxRESTAPIClient(BASE_URL, "id", "secret")


# --- construction -----------------------------------------------------------

def test_client_creates_oauth_session(client):
    assert client._base_url == BASE_URL
    assert client.session.get_base_url() == BASE_URL


# --- list_all_courses -------------------------------------------------------

@responses.activate
def test_list_all_courses_returns_results(client):
    _add_token_response()
    responses.add(
        responses.GET,
        BASE_URL + "/api/courses/v1/courses/",
        json={"results": [{"id": "course-1"}], "pagination": {"next": None}},
        status=200,
    )

    courses = client.list_all_courses()

    assert courses == [{"id": "course-1"}]


@responses.activate
def test_list_all_courses_follows_pagination(client):
    _add_token_response()
    next_url = BASE_URL + "/api/courses/v1/courses/?page=2"
    responses.add(
        responses.GET,
        BASE_URL + "/api/courses/v1/courses/",
        json={"results": [{"id": "course-1"}], "pagination": {"next": next_url}},
        status=200,
    )
    responses.add(
        responses.GET,
        BASE_URL + "/api/courses/v1/courses/",
        json={"results": [{"id": "course-2"}], "pagination": {"next": None}},
        status=200,
    )

    courses = client.list_all_courses()

    assert courses == [{"id": "course-1"}, {"id": "course-2"}]


@responses.activate
def test_list_all_courses_passes_filter_params(client):
    _add_token_response()
    responses.add(
        responses.GET,
        BASE_URL + "/api/courses/v1/courses/",
        json={"results": [], "pagination": {"next": None}},
        status=200,
    )

    client.list_all_courses(org="MyOrg", username="staff", search_term="math")

    api_call = responses.calls[1].request
    assert "org=MyOrg" in api_call.url
    assert "username=staff" in api_call.url
    assert "search_term=math" in api_call.url


@responses.activate
def test_list_all_courses_raises_on_error(client):
    _add_token_response()
    responses.add(
        responses.GET,
        BASE_URL + "/api/courses/v1/courses/",
        status=500,
    )

    with pytest.raises(requests.HTTPError):
        client.list_all_courses()


# --- change_enrollment ------------------------------------------------------

@responses.activate
def test_change_enrollment_returns_json_on_success(client):
    _add_token_response()
    responses.add(
        responses.POST,
        BASE_URL + "/api/bulk_enroll/v1/bulk_enroll",
        json={"action": "enroll"},
        status=200,
    )

    result = client.change_enrollment(
        emails=["a@x.com", "b@x.com"],
        courses=["course-1", "course-2"],
    )

    assert result == {"action": "enroll"}
    sent = responses.calls[1].request
    assert b'"identifiers": "a@x.com,b@x.com"' in sent.body
    assert b'"courses": "course-1,course-2"' in sent.body


@responses.activate
def test_change_enrollment_includes_cohorts_when_given(client):
    _add_token_response()
    responses.add(
        responses.POST,
        BASE_URL + "/api/bulk_enroll/v1/bulk_enroll",
        json={"action": "enroll"},
        status=200,
    )

    client.change_enrollment(
        emails=["a@x.com"], courses=["course-1"], cohorts=["c1", "c2"],
    )

    assert b'"cohorts": "c1,c2"' in responses.calls[1].request.body


@responses.activate
def test_change_enrollment_returns_error_dict_on_failure(client):
    _add_token_response()
    responses.add(
        responses.POST,
        BASE_URL + "/api/bulk_enroll/v1/bulk_enroll",
        body="Bad Request",
        status=400,
    )

    result = client.change_enrollment(emails=["a@x.com"], courses=["course-1"])

    assert result == {"status_code": 400, "response": "Bad Request"}


# --- register_account -------------------------------------------------------

@responses.activate
def test_register_account_posts_form_and_returns_json(client):
    _add_token_response()
    responses.add(
        responses.POST,
        BASE_URL + "/api/user/v1/account/registration/",
        json={"success": True, "redirect_url": "/dashboard"},
        status=200,
    )

    result = client.register_account(
        email="a@x.com", username="alice", name="Alice", password="pw",
    )

    assert result == {"success": True, "redirect_url": "/dashboard"}
    sent = responses.calls[1].request
    assert sent.headers["Content-Type"].startswith("multipart/form-data")


@responses.activate
def test_register_account_includes_extra_kwargs(client):
    _add_token_response()
    responses.add(
        responses.POST,
        BASE_URL + "/api/user/v1/account/registration/",
        json={"success": True},
        status=200,
    )

    client.register_account(
        email="a@x.com", username="alice", name="Alice", password="pw",
        honor_code="true",
    )

    assert b"honor_code" in responses.calls[1].request.body


# --- get_course_grades ------------------------------------------------------

@responses.activate
def test_get_course_grades_returns_list_payload(client):
    _add_token_response()
    responses.add(
        responses.GET,
        BASE_URL + "/api/grades/v1/courses/course-1/",
        json=[{"username": "alice", "percent": 0.9}],
        status=200,
    )

    grades = client.get_course_grades("course-1")

    assert grades == [{"username": "alice", "percent": 0.9}]


@responses.activate
def test_get_course_grades_follows_next_for_dict_payload(client):
    _add_token_response()
    next_url = BASE_URL + "/api/grades/v1/courses/course-1/?page=2"
    responses.add(
        responses.GET,
        BASE_URL + "/api/grades/v1/courses/course-1/",
        json={"results": [{"username": "alice"}], "next": next_url},
        status=200,
    )
    responses.add(
        responses.GET,
        BASE_URL + "/api/grades/v1/courses/course-1/",
        json={"results": [{"username": "bob"}], "next": None},
        status=200,
    )

    grades = client.get_course_grades("course-1")

    assert grades == [{"username": "alice"}, {"username": "bob"}]


@responses.activate
def test_get_course_grades_passes_username(client):
    _add_token_response()
    responses.add(
        responses.GET,
        BASE_URL + "/api/grades/v1/courses/course-1/",
        json=[],
        status=200,
    )

    client.get_course_grades("course-1", username="alice")

    assert "username=alice" in responses.calls[1].request.url


@responses.activate
def test_get_course_grades_raises_on_error(client):
    _add_token_response()
    responses.add(
        responses.GET,
        BASE_URL + "/api/grades/v1/courses/course-1/",
        status=404,
    )

    with pytest.raises(requests.HTTPError):
        client.get_course_grades("course-1")


# --- validation_registration ------------------------------------------------

@responses.activate
def test_validation_registration_returns_json(client):
    _add_token_response()
    responses.add(
        responses.POST,
        BASE_URL + "/api/user/v1/validation/registration",
        json={"validation_decisions": {"username": ""}},
        status=200,
    )

    result = client.validation_registration(username="alice")

    assert result == {"validation_decisions": {"username": ""}}
    assert b'"username": "alice"' in responses.calls[1].request.body
