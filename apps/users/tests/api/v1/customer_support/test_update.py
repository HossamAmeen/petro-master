import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import customer_support_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCustomerSupportUpdate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, customer_support_user):
        self.admin = admin_user
        self.support = customer_support_user
        self.client = auth_client(admin_user)
        self.url = customer_support_detail_url(customer_support_user.id)

    def test_update_name_success(self):
        response = self.client.patch(self.url, {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        self.support.refresh_from_db()
        assert self.support.name == "Renamed"
        assert self.support.updated_by_id == self.admin.id

    def test_update_password_success(self):
        response = self.client.patch(
            self.url,
            {"password": "new-pass-123", "confirm_password": "new-pass-123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.support.refresh_from_db()
        assert self.support.check_password("new-pass-123")
        assert "password" not in response.data

    def test_deactivate_success(self):
        response = self.client.patch(self.url, {"is_active": False}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        self.support.refresh_from_db()
        assert self.support.is_active is False

    def test_update_cannot_change_role_success(self):
        response = self.client.patch(
            self.url, {"role": User.UserRoles.Admin}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.support.refresh_from_db()
        assert self.support.role == User.UserRoles.CustomerSupport

    def test_update_password_mismatch_fail(self):
        response = self.client.patch(
            self.url,
            {"password": "new-pass-123", "confirm_password": "other-pass"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.support.refresh_from_db()
        assert not self.support.check_password("new-pass-123")

    def test_update_other_role_fail(self, finance_user):
        response = self.client.patch(
            customer_support_detail_url(finance_user.id),
            {"name": "Renamed"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        finance_user.refresh_from_db()
        assert finance_user.name != "Renamed"
        assert finance_user.role == User.UserRoles.Finance

    def test_update_without_authentication_fail(self, api_client):
        response = api_client.patch(self.url, {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
    def test_update_non_admin_fail(self, role_fixture, role_client):
        response = role_client(role_fixture).patch(
            self.url, {"name": "Renamed"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.support.refresh_from_db()
        assert self.support.name != "Renamed"
