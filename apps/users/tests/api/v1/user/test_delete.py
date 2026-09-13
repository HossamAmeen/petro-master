import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import users_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestUserDelete:

    def test_delete_without_authentication_fail(self, api_client, finance_user):
        response = api_client.delete(users_detail_url(finance_user.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert User.objects.filter(pk=finance_user.id).exists()

    def test_delete_non_admin_fail(
        self, auth_client, finance_user, customer_support_user
    ):
        response = auth_client(finance_user).delete(
            users_detail_url(customer_support_user.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert User.objects.filter(pk=customer_support_user.id).exists()

    def test_delete_dashboard_user_success(self, auth_client, admin_user, finance_user):
        user_id = finance_user.id

        response = auth_client(admin_user).delete(users_detail_url(user_id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(pk=user_id).exists()

    def test_delete_non_dashboard_user_fail(
        self, auth_client, admin_user, company_owner
    ):
        response = auth_client(admin_user).delete(users_detail_url(company_owner.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert User.objects.filter(pk=company_owner.id).exists()

    def test_delete_unknown_user_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).delete(users_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
