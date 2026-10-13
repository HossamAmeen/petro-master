import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = [pytest.mark.api, pytest.mark.django_db]

LIST_URLS = [
    "stations-list",
    "station-branches-list",
    "services-list",
    "station-owners-list",
    "workers-list",
    "station-branch-managers-list",
    "company-owners-list",
    "company-branch-managers-list",
]


class TestCustomerSupportReadOnly:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, customer_support_user):
        self.client = auth_client(customer_support_user)

    @pytest.mark.parametrize("url_name", LIST_URLS)
    def test_list_success(self, url_name):
        response = self.client.get(reverse(url_name))

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("url_name", LIST_URLS)
    def test_create_forbidden_fail(self, url_name):
        response = self.client.post(reverse(url_name), {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(
        "url_name",
        ["station-gas-operations", "station-other-operations"],
    )
    def test_station_operation_patch_forbidden_fail(self, url_name):
        response = self.client.patch(reverse(url_name, args=[999]), {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_station_operations_list_forbidden_fail(self):
        response = self.client.get(reverse("station-operations"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
