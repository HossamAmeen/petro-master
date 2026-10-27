import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import finance_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestFinanceUpdate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, finance_user):
        self.admin = admin_user
        self.finance = finance_user
        self.client = auth_client(admin_user)
        self.url = finance_detail_url(finance_user.id)

    def test_update_name_success(self):
        response = self.client.patch(self.url, {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        self.finance.refresh_from_db()
        assert self.finance.name == "Renamed"
        assert self.finance.updated_by_id == self.admin.id

    def test_update_password_success(self):
        response = self.client.patch(
            self.url,
            {"password": "new-pass-123", "confirm_password": "new-pass-123"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.finance.refresh_from_db()
        assert self.finance.check_password("new-pass-123")
        assert "password" not in response.data

    def test_deactivate_success(self):
        response = self.client.patch(self.url, {"is_active": False}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        self.finance.refresh_from_db()
        assert self.finance.is_active is False

    def test_update_cannot_change_role_success(self):
        response = self.client.patch(
            self.url, {"role": User.UserRoles.Admin}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.finance.refresh_from_db()
        assert self.finance.role == User.UserRoles.Finance

    def test_update_password_mismatch_fail(self):
        response = self.client.patch(
            self.url,
            {"password": "new-pass-123", "confirm_password": "other-pass"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.finance.refresh_from_db()
        assert not self.finance.check_password("new-pass-123")

    def test_update_other_role_fail(self, customer_support_user):
        response = self.client.patch(
            finance_detail_url(customer_support_user.id),
            {"name": "Renamed"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        customer_support_user.refresh_from_db()
        assert customer_support_user.name != "Renamed"
        assert customer_support_user.role == User.UserRoles.CustomerSupport

    def test_update_without_authentication_fail(self, api_client):
        response = api_client.patch(self.url, {"name": "Renamed"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
    def test_update_non_admin_fail(self, role_fixture, role_client):
        response = role_client(role_fixture).patch(
            self.url, {"name": "Renamed"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.finance.refresh_from_db()
        assert self.finance.name != "Renamed"
