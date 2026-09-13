from decimal import Decimal

import pytest
from rest_framework import status

from .helpers import company_transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {row["id"] for row in response.data["results"]}


class TestCompanyKhaznaTransactionList:
    def test_list_unauthenticated_fail(self, api_client):
        response = api_client.get(company_transaction_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_station_role_forbidden_fail(
        self, auth_client, station_worker, branch
    ):
        response = auth_client(station_worker, station_id=branch.station_id).get(
            company_transaction_list_url()
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_dashboard_user_success(
        self, auth_client, admin_user, company, company_branch, company_transaction_factory
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = auth_client(admin_user).get(company_transaction_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert tx.id in returned_ids(response)

    def test_list_dashboard_user_serializer_uses_dashboard_shape_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, created_by=admin_user
        )

        response = auth_client(admin_user).get(company_transaction_list_url())

        item = next(row for row in response.data["results"] if row["id"] == tx.id)
        assert item["company"] == {"id": company.id, "name": company.name}
        assert item["company_branch"] == {
            "id": company_branch.id,
            "name": company_branch.name,
        }
        assert item["created_by"]["id"] == admin_user.id

    def test_list_company_owner_scoped_to_own_company_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        other_company,
        other_company_branch,
        company_transaction_factory,
    ):
        own_tx = company_transaction_factory(company=company, company_branch=company_branch)
        other_tx = company_transaction_factory(
            company=other_company, company_branch=other_company_branch
        )

        response = auth_client(company_owner, company_id=company.id).get(
            company_transaction_list_url()
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_company_owner_serializer_uses_plain_ids_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = auth_client(company_owner, company_id=company.id).get(
            company_transaction_list_url()
        )

        item = next(row for row in response.data["results"] if row["id"] == tx.id)
        assert item["company"] == company.id
        assert item["company_branch"] == company_branch.id

    def test_list_company_branch_manager_scoped_to_managed_branch_success(
        self,
        auth_client,
        company_branch_manager,
        company,
        company_branch,
        second_company_branch,
        company_transaction_factory,
    ):
        managed_tx = company_transaction_factory(
            company=company, company_branch=company_branch
        )
        other_branch_tx = company_transaction_factory(
            company=company, company_branch=second_company_branch
        )

        response = auth_client(company_branch_manager, company_id=company.id).get(
            company_transaction_list_url()
        )

        ids = returned_ids(response)
        assert managed_tx.id in ids
        assert other_branch_tx.id not in ids

    def test_list_filter_by_status_success(
        self, auth_client, admin_user, company, company_branch, company_transaction_factory
    ):
        approved = company_transaction_factory(
            company=company, company_branch=company_branch, status="approved"
        )
        pending = company_transaction_factory(
            company=company, company_branch=company_branch, status="pending"
        )

        response = auth_client(admin_user).get(
            company_transaction_list_url() + "?status=approved"
        )

        ids = returned_ids(response)
        assert approved.id in ids
        assert pending.id not in ids

    def test_list_filter_by_is_incoming_success(
        self, auth_client, admin_user, company, company_branch, company_transaction_factory
    ):
        incoming = company_transaction_factory(
            company=company, company_branch=company_branch, is_incoming=True
        )
        outgoing = company_transaction_factory(
            company=company, company_branch=company_branch, is_incoming=False
        )

        response = auth_client(admin_user).get(
            company_transaction_list_url() + "?is_incoming=true"
        )

        ids = returned_ids(response)
        assert incoming.id in ids
        assert outgoing.id not in ids

    def test_list_filter_by_company_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        other_company,
        other_company_branch,
        company_transaction_factory,
    ):
        own_tx = company_transaction_factory(company=company, company_branch=company_branch)
        other_tx = company_transaction_factory(
            company=other_company, company_branch=other_company_branch
        )

        response = auth_client(admin_user).get(
            company_transaction_list_url() + f"?company={company.id}"
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_search_by_company_name_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        other_company,
        other_company_branch,
        company_transaction_factory,
    ):
        own_tx = company_transaction_factory(company=company, company_branch=company_branch)
        other_tx = company_transaction_factory(
            company=other_company, company_branch=other_company_branch
        )

        response = auth_client(admin_user).get(
            company_transaction_list_url() + f"?search={company.name}"
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_filter_by_is_unpaid_success(
        self, auth_client, admin_user, company, company_branch, company_transaction_factory
    ):
        unpaid = company_transaction_factory(
            company=company, company_branch=company_branch, is_unpaid=True
        )
        paid = company_transaction_factory(
            company=company, company_branch=company_branch, is_unpaid=False
        )

        response = auth_client(admin_user).get(
            company_transaction_list_url() + "?is_unpaid=true"
        )

        ids = returned_ids(response)
        assert unpaid.id in ids
        assert paid.id not in ids

    def test_list_empty_for_company_owner_with_no_transactions_success(
        self, auth_client, company_owner, company
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            company_transaction_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []
