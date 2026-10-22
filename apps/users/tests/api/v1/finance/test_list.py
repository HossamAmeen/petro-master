import pytest
from rest_framework import status

from apps.users.models import Finance, User
from apps.users.tests.helpers import finance_list_url, returned_ids, user_ref

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


class TestFinanceList:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, finance_user):
        self.admin = admin_user
        self.finance = finance_user
        self.client = auth_client(admin_user)

    def test_list_only_finance_users_success(
        self, finance_user, company_owner, station_worker
    ):
        response = self.client.get(finance_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == [
            {
                "id": self.finance.id,
                "name": self.finance.name,
                "email": self.finance.email,
                "phone_number": self.finance.phone_number,
                "role": User.UserRoles.Finance,
                "created": response.data["results"][0]["created"],
                "modified": response.data["results"][0]["modified"],
                "is_active": True,
                "created_by": user_ref(self.admin),
                "updated_by": None,
            }
        ]

    def test_list_newest_first_success(self):
        newer = Finance.objects.create(
            name="Newer Support",
            phone_number="01700000001",
            email="newer-finance@example.com",
        )

        response = self.client.get(finance_list_url())

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert ids == [newer.id, self.finance.id]

    def test_list_filter_by_is_active_success(self):
        inactive = Finance.objects.create(
            name="Inactive Support",
            phone_number="01700000002",
            email="inactive-finance@example.com",
            is_active=False,
        )

        response = self.client.get(finance_list_url(is_active="false"))

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {inactive.id}

    def test_list_search_by_phone_success(self):
        Finance.objects.create(
            name="Other Support",
            phone_number="01700000003",
            email="other-finance@example.com",
        )

        response = self.client.get(finance_list_url(search=self.finance.phone_number))

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {self.finance.id}

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(finance_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize("role_fixture", NON_ADMIN_ROLES)
    def test_list_non_admin_fail(self, role_fixture, role_client):
        response = role_client(role_fixture).get(finance_list_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN
