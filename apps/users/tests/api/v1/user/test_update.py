import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import users_detail_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_update_without_authentication_fail(api_client, finance_user):
    response = api_client.patch(
        users_detail_url(finance_user.id),
        {"name": "Hacker"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_non_admin_fail(auth_client, finance_user):
    response = auth_client(finance_user).patch(
        users_detail_url(finance_user.id),
        {"name": "Nope"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    finance_user.refresh_from_db()
    assert finance_user.name != "Nope"


def test_update_name_success(auth_client, admin_user, finance_user):
    response = auth_client(admin_user).patch(
        users_detail_url(finance_user.id),
        {"name": "Updated Finance"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    finance_user.refresh_from_db()
    assert finance_user.name == "Updated Finance"
    assert finance_user.updated_by_id == admin_user.id


def test_update_password_success(auth_client, admin_user, finance_user):
    response = auth_client(admin_user).patch(
        users_detail_url(finance_user.id),
        {"password": "new-pass-123", "confirm_password": "new-pass-123"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    finance_user.refresh_from_db()
    assert finance_user.check_password("new-pass-123")
    assert "password" not in response.data


def test_update_password_mismatch_fail(auth_client, admin_user, finance_user):
    response = auth_client(admin_user).patch(
        users_detail_url(finance_user.id),
        {"password": "new-pass-123", "confirm_password": "other-pass"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    finance_user.refresh_from_db()
    assert not finance_user.check_password("new-pass-123")


def test_update_password_without_confirm_fail(auth_client, admin_user, finance_user):
    response = auth_client(admin_user).patch(
        users_detail_url(finance_user.id),
        {"password": "new-pass-123"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_update_non_dashboard_user_fail(auth_client, admin_user, company_owner):
    response = auth_client(admin_user).patch(
        users_detail_url(company_owner.id),
        {"name": "Should Not Update"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    company_owner.refresh_from_db()
    assert company_owner.name != "Should Not Update"


def test_update_role_success(auth_client, admin_user, finance_user):
    response = auth_client(admin_user).patch(
        users_detail_url(finance_user.id),
        {"role": User.UserRoles.CustomerSupport},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    finance_user.refresh_from_db()
    assert finance_user.role == User.UserRoles.CustomerSupport
