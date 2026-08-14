import pytest
from django.urls import reverse

from apps.companies.factories import DriverFactory


@pytest.mark.api
@pytest.mark.django_db
class TestDriverAPI:
    def test_list_requires_authentication(self, api_client):
        response = api_client.get(reverse("drivers-list"))

        assert response.status_code == 401

    def test_company_owner_sees_drivers_from_own_company(
        self, auth_client, company_owner, company, company_branch, admin_user
    ):
        owned_driver = DriverFactory(
            branch=company_branch,
            created_by=admin_user,
            updated_by=admin_user,
        )

        client = auth_client(company_owner, company_id=company.id)
        response = client.get(reverse("drivers-list"))

        assert response.status_code == 200
        returned_driver_ids = {driver["id"] for driver in response.data["results"]}
        assert owned_driver.id in returned_driver_ids
