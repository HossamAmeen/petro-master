import pytest
from rest_framework import status

from .helpers import company_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyKhaznaTransactionRetrieve:
    def test_retrieve_unauthenticated_fail(
        self, api_client, company, company_branch, company_transaction_factory
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = api_client.get(company_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_not_found_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(company_transaction_detail_url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_station_role_forbidden_fail(
        self,
        auth_client,
        station_worker,
        branch,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = auth_client(station_worker, station_id=branch.station_id).get(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_dashboard_user_success(
        self, auth_client, admin_user, company, company_branch, company_transaction_factory
    ):
        tx = company_transaction_factory(
            company=company,
            company_branch=company_branch,
            created_by=admin_user,
            updated_by=admin_user,
        )

        response = auth_client(admin_user).get(company_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["company"] == {"id": company.id, "name": company.name}
        assert response.data["company_branch"] == {
            "id": company_branch.id,
            "name": company_branch.name,
        }
        assert response.data["created_by"]["id"] == admin_user.id
        assert response.data["updated_by"]["id"] == admin_user.id
        assert "reference_code" in response.data
        assert response.data["reference_code"] == tx.reference_code

    def test_retrieve_company_owner_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        company_transaction_factory,
        admin_user,
    ):
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, created_by=admin_user
        )

        response = auth_client(company_owner, company_id=company.id).get(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["company"] == company.id
        assert response.data["company_branch"] == company_branch.id
        assert response.data["created_by"] == admin_user.id

    def test_retrieve_company_owner_cannot_see_other_company_transaction_fail(
        self,
        auth_client,
        company_owner,
        company,
        other_company,
        other_company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=other_company, company_branch=other_company_branch
        )

        response = auth_client(company_owner, company_id=company.id).get(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_company_branch_manager_cannot_see_unmanaged_branch_fail(
        self,
        auth_client,
        company_branch_manager,
        company,
        second_company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=company, company_branch=second_company_branch
        )

        response = auth_client(company_branch_manager, company_id=company.id).get(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_company_branch_manager_managed_branch_success(
        self,
        auth_client,
        company_branch_manager,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = auth_client(company_branch_manager, company_id=company.id).get(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
