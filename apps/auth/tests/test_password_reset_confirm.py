from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status

from apps.auth.tests.helpers import (
    LOGIN_PASSWORD,
    company_login_url,
    login_payload,
    password_reset_confirm_url,
    set_login_password,
)
from apps.companies.factories import UserFactory


pytestmark = [pytest.mark.api, pytest.mark.django_db]


NEW_PASSWORD = "new-pass-123"


def _reset_payload(password=NEW_PASSWORD, confirm_password=None):
    return {
        "password": password,
        "confirm_password": password if confirm_password is None else confirm_password,
    }


def test_password_reset_confirm_get_valid_token_success(api_client):
    user = UserFactory()
    token = user.create_password_reset_token()

    response = api_client.get(password_reset_confirm_url(token))

    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/html")
    assert b'id="passwordForm"' in response.content
    assert b"Invalid or expired token." not in response.content


def test_password_reset_confirm_get_unknown_token_fail(api_client):
    response = api_client.get(password_reset_confirm_url("missing-token"))

    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"].startswith("text/html")
    assert b"Invalid or expired token." in response.content
    assert b'id="passwordForm"' not in response.content


def test_password_reset_confirm_get_expired_token_still_renders_form_success(api_client):
    user = UserFactory()
    token = user.create_password_reset_token()
    user.reset_password_token_created_at = timezone.localtime() - timedelta(hours=25)
    user.save(update_fields=["reset_password_token_created_at"])

    response = api_client.get(password_reset_confirm_url(token))

    assert response.status_code == status.HTTP_200_OK
    assert b'id="passwordForm"' in response.content


def test_password_reset_confirm_post_valid_token_success(api_client):
    user = UserFactory()
    set_login_password(user)
    token = user.create_password_reset_token()

    response = api_client.post(
        password_reset_confirm_url(token),
        _reset_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {"detail": "Password reset successful."}
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(LOGIN_PASSWORD)
    assert user.reset_password_token is None
    assert user.reset_password_token_created_at is None


def test_password_reset_confirm_allows_login_with_new_password_success(api_client, company_owner):
    set_login_password(company_owner)
    token = company_owner.create_password_reset_token()

    response = api_client.post(
        password_reset_confirm_url(token),
        _reset_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    login_response = api_client.post(
        company_login_url(),
        login_payload(company_owner, password=NEW_PASSWORD),
        format="json",
    )
    assert login_response.status_code == status.HTTP_200_OK, login_response.data


def test_password_reset_confirm_cannot_reuse_token_fail(api_client):
    user = UserFactory()
    token = user.create_password_reset_token()
    first = api_client.post(
        password_reset_confirm_url(token),
        _reset_payload(),
        format="json",
    )
    assert first.status_code == status.HTTP_200_OK

    response = api_client.post(
        password_reset_confirm_url(token),
        _reset_payload(password="another-pass"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {"detail": "Invalid reset link."}


def test_password_reset_confirm_unknown_token_fail(api_client):
    response = api_client.post(
        password_reset_confirm_url("missing-token"),
        _reset_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {"detail": "Invalid reset link."}


def test_password_reset_confirm_expired_token_fail(api_client):
    user = UserFactory()
    token = user.create_password_reset_token()
    user.reset_password_token_created_at = timezone.localtime() - timedelta(hours=24)
    user.save(update_fields=["reset_password_token_created_at"])

    response = api_client.post(
        password_reset_confirm_url(token),
        _reset_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {"detail": "Invalid or expired reset link."}
    user.refresh_from_db()
    assert not user.check_password(NEW_PASSWORD)
    assert user.reset_password_token == token


def test_password_reset_confirm_password_mismatch_fail(api_client):
    user = UserFactory()
    token = user.create_password_reset_token()

    response = api_client.post(
        password_reset_confirm_url(token),
        _reset_payload(confirm_password="different-pass"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
    user.refresh_from_db()
    assert user.reset_password_token == token


def test_password_reset_confirm_password_too_short_fail(api_client):
    user = UserFactory()
    token = user.create_password_reset_token()

    response = api_client.post(
        password_reset_confirm_url(token),
        {"password": "short", "confirm_password": "short"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"


@pytest.mark.parametrize("missing_field", ["password", "confirm_password"])
def test_password_reset_confirm_missing_field_fail(api_client, missing_field):
    user = UserFactory()
    token = user.create_password_reset_token()
    payload = _reset_payload()
    payload.pop(missing_field)

    response = api_client.post(
        password_reset_confirm_url(token),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "validation_error"
