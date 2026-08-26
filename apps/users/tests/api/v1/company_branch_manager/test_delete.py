import pytest
from rest_framework import status

from apps.users.models import CompanyUser
from apps.users.tests.helpers import company_branch_managers_detail_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyBranchManagerDelete:


    def test_delete_without_authentication_fail(self, api_client, company_branch_manager):
        response = api_client.delete(
            company_branch_managers_detail_url(company_branch_manager.id)
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CompanyUser.objects.filter(pk=company_branch_manager.id).exists()


    def test_delete_as_station_owner_fail(self,
        auth_client, station_owner, station, company_branch_manager
    ):
        response = auth_client(station_owner, station_id=station.id).delete(
            company_branch_managers_detail_url(company_branch_manager.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CompanyUser.objects.filter(pk=company_branch_manager.id).exists()


    def test_delete_as_company_owner_success(self,
        auth_client, company_owner, company, company_branch_manager
    ):
        user_id = company_branch_manager.id

        response = auth_client(company_owner, company_id=company.id).delete(
            company_branch_managers_detail_url(user_id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CompanyUser.objects.filter(pk=user_id).exists()


    def test_delete_other_company_as_owner_fail(self,
        auth_client, company_owner, company, other_company_branch_manager
    ):
        response = auth_client(company_owner, company_id=company.id).delete(
            company_branch_managers_detail_url(other_company_branch_manager.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert CompanyUser.objects.filter(pk=other_company_branch_manager.id).exists()
