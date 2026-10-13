import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import customer_support_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCustomerSupportDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, customer_support_user):
        self.support = customer_support_user
        self.client = auth_client(admin_user)
        self.url = customer_support_detail_url(customer_support_user.id)

    def test_delete_success(self):
        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not User.objects.filter(pk=self.support.id).exists()

    def test_delete_other_role_fail(self, finance_user):
        response = self.client.delete(customer_support_detail_url(finance_user.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert User.objects.filter(pk=finance_user.id).exists()

    def test_delete_without_authentication_fail(self, api_client):
        response = api_client.delete(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert User.objects.filter(pk=self.support.id).exists()

    @pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
    def test_delete_non_admin_fail(self, role_fixture, role_client):
        response = role_client(role_fixture).delete(self.url)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert User.objects.filter(pk=self.support.id).exists()
