import pytest
from rest_framework import status

from .helpers import company_transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {row["id"] for row in response.data["results"]}


class TestCompanyKhaznaTransactionList:
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
        self.url = company_transaction_list_url()

    def list(self, client=None, query=""):
        return (client or self.admin_client).get(self.url + query)

    def own_transaction(self, **overrides):
        return self.create_transaction(
            company=self.company, company_branch=self.company_branch, **overrides
        )

    def test_list_unauthenticated_fail(self, api_client):
        response = self.list(client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_station_role_forbidden_fail(self, station_worker, branch):
        client = self.auth_client(station_worker, station_id=branch.station_id)

        response = self.list(client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_dashboard_user_success(self):
        tx = self.own_transaction()

        response = self.list()

        assert response.status_code == status.HTTP_200_OK
        assert tx.id in returned_ids(response)

    def test_list_dashboard_user_serializer_uses_dashboard_shape_success(self):
        tx = self.own_transaction(created_by=self.admin)

        response = self.list()

        item = next(row for row in response.data["results"] if row["id"] == tx.id)
        assert item["company"] == {"id": self.company.id, "name": self.company.name}
        assert item["company_branch"] == {
            "id": self.company_branch.id,
            "name": self.company_branch.name,
        }
        assert item["created_by"]["id"] == self.admin.id

    def test_list_company_owner_scoped_to_own_company_success(
        self, company_owner, other_company, other_company_branch
    ):
        own_tx = self.own_transaction()
        other_tx = self.create_transaction(
            company=other_company, company_branch=other_company_branch
        )

        response = self.list(
            client=self.auth_client(company_owner, company_id=self.company.id)
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_company_owner_serializer_uses_plain_ids_success(self, company_owner):
        tx = self.own_transaction()

        response = self.list(
            client=self.auth_client(company_owner, company_id=self.company.id)
        )

        item = next(row for row in response.data["results"] if row["id"] == tx.id)
        assert item["company"] == self.company.id
        assert item["company_branch"] == self.company_branch.id

    def test_list_company_branch_manager_scoped_to_managed_branch_success(
        self, company_branch_manager, second_company_branch
    ):
        managed_tx = self.own_transaction()
        other_branch_tx = self.create_transaction(
            company=self.company, company_branch=second_company_branch
        )

        response = self.list(
            client=self.auth_client(company_branch_manager, company_id=self.company.id)
        )

        ids = returned_ids(response)
        assert managed_tx.id in ids
        assert other_branch_tx.id not in ids

    def test_list_filter_by_status_success(self):
        approved = self.own_transaction(status="approved")
        pending = self.own_transaction(status="pending")

        response = self.list(query="?status=approved")

        ids = returned_ids(response)
        assert approved.id in ids
        assert pending.id not in ids

    def test_list_filter_by_is_incoming_success(self):
        incoming = self.own_transaction(is_incoming=True)
        outgoing = self.own_transaction(is_incoming=False)

        response = self.list(query="?is_incoming=true")

        ids = returned_ids(response)
        assert incoming.id in ids
        assert outgoing.id not in ids

    def test_list_filter_by_company_success(self, other_company, other_company_branch):
        own_tx = self.own_transaction()
        other_tx = self.create_transaction(
            company=other_company, company_branch=other_company_branch
        )

        response = self.list(query=f"?company={self.company.id}")

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_search_by_company_name_success(
        self, other_company, other_company_branch
    ):
        own_tx = self.own_transaction()
        other_tx = self.create_transaction(
            company=other_company, company_branch=other_company_branch
        )

        response = self.list(query=f"?search={self.company.name}")

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_filter_by_is_unpaid_success(self):
        unpaid = self.own_transaction(is_unpaid=True)
        paid = self.own_transaction(is_unpaid=False)

        response = self.list(query="?is_unpaid=true")

        ids = returned_ids(response)
        assert unpaid.id in ids
        assert paid.id not in ids

    def test_list_empty_for_company_owner_with_no_transactions_success(
        self, company_owner
    ):
        response = self.list(
            client=self.auth_client(company_owner, company_id=self.company.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []
