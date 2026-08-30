import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import company_branch_managers_detail_url, user_ref


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyBranchManagerRetrieve:


    def test_retrieve_without_authentication_fail(self, api_client, company_branch_manager):
        response = api_client.get(
            company_branch_managers_detail_url(company_branch_manager.id)
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_retrieve_as_station_owner_fail(self,
        auth_client, station_owner, station, company_branch_manager
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            company_branch_managers_detail_url(company_branch_manager.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


    def test_retrieve_includes_managed_branches_success(self,
        auth_client, admin_user, company_branch_manager, company, company_branch
    ):
        response = auth_client(admin_user).get(
            company_branch_managers_detail_url(company_branch_manager.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_branch_manager.id
        assert response.data["name"] == company_branch_manager.name
        assert response.data["role"] == User.UserRoles.CompanyBranchManager
        assert response.data["company_id"] == company.id
        assert response.data["created_by"] == user_ref(admin_user)
        assert response.data["company_branches"] == [
            {"id": company_branch.id, "name": company_branch.name}
        ]


    def test_retrieve_other_company_as_owner_fail(self,
        auth_client, company_owner, company, other_company_branch_manager
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            company_branch_managers_detail_url(other_company_branch_manager.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


    def test_retrieve_unknown_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(
            company_branch_managers_detail_url(999_999)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
