import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import customer_support_detail_url, user_ref

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCustomerSupportRetrieve:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, customer_support_user):
        self.admin = admin_user
        self.support = customer_support_user
        self.client = auth_client(admin_user)

    def test_retrieve_success(self):
        response = self.client.get(customer_support_detail_url(self.support.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.support.id
        assert response.data["name"] == self.support.name
        assert response.data["email"] == self.support.email
        assert response.data["phone_number"] == self.support.phone_number
        assert response.data["role"] == User.UserRoles.CustomerSupport
        assert response.data["created_by"] == user_ref(self.admin)
        assert "password" not in response.data

    @pytest.mark.parametrize("user_fixture", ["finance_user", "company_owner"])
    def test_retrieve_other_role_fail(self, user_fixture, request):
        user = request.getfixturevalue(user_fixture)

        response = self.client.get(customer_support_detail_url(user.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_without_authentication_fail(self, api_client):
        response = api_client.get(customer_support_detail_url(self.support.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_as_customer_support_fail(self, auth_client):
        response = auth_client(self.support).get(
            customer_support_detail_url(self.support.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
