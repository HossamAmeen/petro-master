import pytest
from rest_framework import status

from .helpers import company_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyKhaznaTransactionRetrieve:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        self.auth_client = auth_client
        self.admin = admin_user
        self.admin_client = auth_client(admin_user)
        self.company = company
        self.company_branch = company_branch
        self.create_transaction = company_transaction_factory

    def retrieve(self, pk, client=None):
        return (client or self.admin_client).get(company_transaction_detail_url(pk))

    def own_transaction(self, **overrides):
        return self.create_transaction(
            company=self.company, company_branch=self.company_branch, **overrides
        )

    def company_client(self, user):
        return self.auth_client(user, company_id=self.company.id)

    def test_retrieve_unauthenticated_fail(self, api_client):
        tx = self.own_transaction()

        response = self.retrieve(tx.id, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_not_found_fail(self):
        response = self.retrieve(999999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_station_role_forbidden_fail(self, station_worker, branch):
        tx = self.own_transaction()
        client = self.auth_client(station_worker, station_id=branch.station_id)

        response = self.retrieve(tx.id, client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_dashboard_user_success(self):
        tx = self.own_transaction(created_by=self.admin, updated_by=self.admin)

        response = self.retrieve(tx.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["company"] == {
            "id": self.company.id,
            "name": self.company.name,
        }
        assert response.data["company_branch"] == {
            "id": self.company_branch.id,
            "name": self.company_branch.name,
        }
        assert response.data["created_by"]["id"] == self.admin.id
        assert response.data["updated_by"]["id"] == self.admin.id
        assert "reference_code" in response.data
        assert response.data["reference_code"] == tx.reference_code

    def test_retrieve_company_owner_success(self, company_owner):
        tx = self.own_transaction(created_by=self.admin)

        response = self.retrieve(tx.id, client=self.company_client(company_owner))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["company"] == self.company.id
        assert response.data["company_branch"] == self.company_branch.id
        assert response.data["created_by"] == self.admin.id

    def test_retrieve_company_owner_cannot_see_other_company_transaction_fail(
        self, company_owner, other_company, other_company_branch
    ):
        tx = self.create_transaction(
            company=other_company, company_branch=other_company_branch
        )

        response = self.retrieve(tx.id, client=self.company_client(company_owner))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_company_branch_manager_cannot_see_unmanaged_branch_fail(
        self, company_branch_manager, second_company_branch
    ):
        tx = self.create_transaction(
            company=self.company, company_branch=second_company_branch
        )

        response = self.retrieve(
            tx.id, client=self.company_client(company_branch_manager)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_company_branch_manager_managed_branch_success(
        self, company_branch_manager
    ):
        tx = self.own_transaction()

        response = self.retrieve(
            tx.id, client=self.company_client(company_branch_manager)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
