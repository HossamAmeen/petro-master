from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def company_detail_url(company_id):
    return reverse("companies-detail", kwargs={"pk": company_id})


class TestCompanyRetrieve:


    def test_retrieve_without_authentication_fail(self, api_client, company):
        response = api_client.get(company_detail_url(company.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_retrieve_company_success(self,
        auth_client,
        admin_user,
        company,
        geo_data,
    ):
        response = auth_client(admin_user).get(company_detail_url(company.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company.id
        assert response.data["name"] == company.name
        assert response.data["address"] == company.address
        assert Decimal(str(response.data["balance"])) == Decimal("0.00")
        assert response.data["is_active"] is True
        assert response.data["district"]["id"] == geo_data["district"].id
        assert response.data["district"]["city"]["id"] == geo_data["city"].id
        assert response.data["created_by"]["id"] == admin_user.id
        assert response.data["total_branches"] == 0
        assert response.data["total_cars"] == 0
        assert response.data["total_drivers"] == 0
        assert response.data["total_managers"] == 0


    def test_retrieve_company_with_related_counts_success(self,
        auth_client,
        admin_user,
        company,
        company_branch,
        second_company_branch,
        company_car,
        company_driver,
        company_branch_manager,
    ):
        response = auth_client(admin_user).get(company_detail_url(company.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_branches"] == 2
        assert response.data["total_cars"] == 1
        assert response.data["total_drivers"] == 1
        assert response.data["total_managers"] == 1


    def test_retrieve_other_company_as_company_owner_success(self,
        auth_client,
        company_owner,
        company,
        other_company,
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            company_detail_url(other_company.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == other_company.id


    def test_retrieve_unknown_company_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(company_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
