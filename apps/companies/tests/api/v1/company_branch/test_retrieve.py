from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def branch_detail_url(branch_id):
    return reverse("company-branches-detail", kwargs={"pk": branch_id})


class TestCompanyBranchRetrieve:

    def test_retrieve_without_authentication_fail(self, api_client, company_branch):
        response = api_client.get(branch_detail_url(company_branch.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_branch_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        geo_data,
    ):
        response = auth_client(admin_user).get(branch_detail_url(company_branch.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_branch.id
        assert response.data["name"] == company_branch.name
        assert response.data["company"]["id"] == company.id
        assert response.data["district"]["id"] == geo_data["district"].id
        assert Decimal(str(response.data["balance"])) == Decimal("0.00")
        assert response.data["cars_count"] == 0
        assert response.data["drivers_count"] == 0
        assert response.data["managers_count"] == 0
        assert response.data["managers"] == []

    def test_retrieve_branch_with_related_counts_success(
        self,
        auth_client,
        admin_user,
        company_branch,
        company_car,
        company_driver,
        company_branch_manager,
    ):
        response = auth_client(admin_user).get(branch_detail_url(company_branch.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["cars_count"] == 1
        assert response.data["drivers_count"] == 1
        assert response.data["managers_count"] == 1
        assert response.data["managers"][0]["id"] == company_branch_manager.id

    def test_retrieve_owned_branch_as_company_owner_success(
        self, auth_client, company_owner, company, company_branch
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            branch_detail_url(company_branch.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_branch.id

    def test_retrieve_other_company_branch_as_owner_fail(
        self, auth_client, company_owner, company, other_company_branch
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            branch_detail_url(other_company_branch.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_unmanaged_branch_as_branch_manager_fail(
        self, auth_client, company_branch_manager, company, second_company_branch
    ):
        response = auth_client(company_branch_manager, company_id=company.id).get(
            branch_detail_url(second_company_branch.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_managed_branch_as_branch_manager_success(
        self, auth_client, company_branch_manager, company, company_branch
    ):
        response = auth_client(company_branch_manager, company_id=company.id).get(
            branch_detail_url(company_branch.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_branch.id

    def test_retrieve_any_branch_as_station_worker_success(
        self, auth_client, station_worker, station, other_company_branch
    ):
        response = auth_client(station_worker, station_id=station.id).get(
            branch_detail_url(other_company_branch.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == other_company_branch.id

    def test_retrieve_unknown_branch_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(branch_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
