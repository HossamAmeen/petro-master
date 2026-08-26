import pytest
from rest_framework import status

from apps.auth.tests.helpers import (
    LOGIN_PASSWORD,
    dashboard_login_url,
    decode_access,
    login_payload,
    set_login_password,
)


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _login(api_client, user, **payload_kwargs):
    set_login_password(user)
    return api_client.post(
        dashboard_login_url(),
        login_payload(user, **payload_kwargs),
        format="json",
    )


@pytest.mark.parametrize(
    "role_fixture",
    ["finance_user", "customer_support_user"],
)
def test_dashboard_login_with_email_success(role_fixture, request, api_client):
    user = request.getfixturevalue(role_fixture)

    response = _login(api_client, user)

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["user_name"] == user.name
    assert response.data["role"] == user.role
    assert "company_id" not in response.data
    assert "station_id" not in response.data
    access = decode_access(response.data["access"])
    assert access["user_name"] == user.name
    assert access["role"] == user.role
    assert "company_id" not in access
    assert "station_id" not in access


def test_dashboard_login_with_phone_number_success(api_client, admin_user):
    response = _login(api_client, admin_user, identifier=admin_user.phone_number)

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["user_name"] == admin_user.name
    assert response.data["role"] == admin_user.role
    assert "company_id" not in response.data
    assert "station_id" not in response.data
    access = decode_access(response.data["access"])
    assert access["user_name"] == admin_user.name
    assert access["role"] == admin_user.role


@pytest.mark.parametrize("missing_field", ["identifier", "password"])
def test_dashboard_login_missing_field_fail(api_client, admin_user, missing_field):
    set_login_password(admin_user)
    payload = login_payload(admin_user)
    payload.pop(missing_field)

    response = api_client.post(dashboard_login_url(), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"


def test_dashboard_login_wrong_password_fail(api_client, admin_user):
    response = _login(api_client, admin_user, password="wrong-password")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "invalid_credentials"
    assert response.data["message"] == "Invalid credentials"


def test_dashboard_login_unknown_identifier_fail(api_client):
    response = api_client.post(
        dashboard_login_url(),
        {"identifier": "nobody@example.com", "password": LOGIN_PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "invalid_credentials"


def test_dashboard_login_inactive_admin_fail(api_client, admin_user):
    set_login_password(admin_user)
    admin_user.is_active = False
    admin_user.save(update_fields=["is_active"])

    response = api_client.post(
        dashboard_login_url(),
        login_payload(admin_user),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "invalid_credentials"


@pytest.mark.parametrize(
    "role_fixture",
    [
        "company_owner",
        "company_branch_manager",
        "station_owner",
        "branch_manager",
        "station_worker",
        "driver_user",
        "supervisor",
        "agent",
    ],
)
def test_dashboard_login_wrong_role_fail(role_fixture, request, api_client):
    user = request.getfixturevalue(role_fixture)

    response = _login(api_client, user)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.data["code"] == "invalid_credentials"


def test_dashboard_login_get_method_fail(api_client):
    response = api_client.get(dashboard_login_url())

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
