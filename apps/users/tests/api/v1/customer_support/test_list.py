import pytest
from rest_framework import status

from apps.users.models import CustomerSupport, User
from apps.users.tests.helpers import customer_support_list_url, returned_ids, user_ref

pytestmark = [pytest.mark.api, pytest.mark.django_db]

NON_ADMIN_ROLES = [
    "finance_user",
    "customer_support_user",
    "company_owner",
    "company_branch_manager",
    "station_owner",
    "branch_manager",
    "station_worker",
]


class TestCustomerSupportList:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, customer_support_user):
        self.admin = admin_user
        self.support = customer_support_user
        self.client = auth_client(admin_user)

    def test_list_only_customer_support_users_success(
        self, finance_user, company_owner, station_worker
    ):
        response = self.client.get(customer_support_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == [
            {
                "id": self.support.id,
                "name": self.support.name,
                "email": self.support.email,
                "phone_number": self.support.phone_number,
                "role": User.UserRoles.CustomerSupport,
                "created": response.data["results"][0]["created"],
                "modified": response.data["results"][0]["modified"],
                "is_active": True,
                "created_by": user_ref(self.admin),
                "updated_by": None,
            }
        ]

    def test_list_newest_first_success(self):
        newer = CustomerSupport.objects.create(
            name="Newer Support",
            phone_number="01700000001",
            email="newer-support@example.com",
        )

        response = self.client.get(customer_support_list_url())

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert ids == [newer.id, self.support.id]

    def test_list_filter_by_is_active_success(self):
        inactive = CustomerSupport.objects.create(
            name="Inactive Support",
            phone_number="01700000002",
            email="inactive-support@example.com",
            is_active=False,
        )

        response = self.client.get(customer_support_list_url(is_active="false"))

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {inactive.id}

    def test_list_search_by_phone_success(self):
        CustomerSupport.objects.create(
            name="Other Support",
            phone_number="01700000003",
            email="other-support@example.com",
        )

        response = self.client.get(
            customer_support_list_url(search=self.support.phone_number)
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {self.support.id}

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(customer_support_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("role_fixture", NON_ADMIN_ROLES)
    def test_list_non_admin_fail(self, role_fixture, role_client):
        response = role_client(role_fixture).get(customer_support_list_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN
