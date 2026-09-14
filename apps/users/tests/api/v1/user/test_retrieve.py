import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import users_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestUserRetrieve:

    def test_retrieve_without_authentication_fail(self, api_client, finance_user):
        response = api_client.get(users_detail_url(finance_user.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_non_admin_fail(
        self, auth_client, finance_user, customer_support_user
    ):
        response = auth_client(finance_user).get(
            users_detail_url(customer_support_user.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_dashboard_user_success(
        self, auth_client, admin_user, finance_user
    ):
        response = auth_client(admin_user).get(users_detail_url(finance_user.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == finance_user.name
        assert response.data["email"] == finance_user.email
        assert response.data["phone_number"] == finance_user.phone_number
        assert response.data["role"] == User.UserRoles.Finance
        assert "password" not in response.data

    def test_retrieve_non_dashboard_user_fail(
        self, auth_client, admin_user, company_owner
    ):
        response = auth_client(admin_user).get(users_detail_url(company_owner.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_unknown_user_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(users_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
