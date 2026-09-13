import pytest
from django.core.exceptions import FieldError
from rest_framework import status

from .helpers import transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionList:
    """`KhaznaTransactionViewSet` is authenticated-only (`IsAuthenticated`) with
    no role permission restriction. Its `get_queryset` only special-cases
    `CompanyOwner`/`CompanyBranchManager`, and every other authenticated role
    (dashboard, station roles) receives the full, unscoped queryset."""

    def test_list_unauthenticated_fail(self, api_client):
        response = api_client.get(transaction_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_dashboard_user_success(
        self, auth_client, admin_user, khazna_transaction_factory
    ):
        tx = khazna_transaction_factory()

        response = auth_client(admin_user).get(transaction_list_url())

        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert any(row["id"] == tx.id for row in results)

    def test_list_includes_rows_created_via_company_and_station_transactions_success(
        self,
        auth_client,
        admin_user,
        company_transaction_factory,
        station_transaction_factory,
    ):
        company_tx = company_transaction_factory()
        station_tx = station_transaction_factory()

        response = auth_client(admin_user).get(transaction_list_url())

        ids = {row["id"] for row in response.data["results"]}
        assert company_tx.id in ids
        assert station_tx.id in ids
        # The base serializer only exposes base-model fields.
        row = next(row for row in response.data["results"] if row["id"] == company_tx.id)
        assert "company" not in row
        assert "company_branch" not in row

    def test_list_station_owner_sees_unscoped_queryset_success(
        self,
        auth_client,
        station_owner,
        station,
        khazna_transaction_factory,
    ):
        """Documents actual behavior: station roles are not filtered by
        `KhaznaTransactionViewSet.get_queryset`, so a station owner can see
        every khazna transaction in the system, not just their own."""
        tx = khazna_transaction_factory()

        response = auth_client(station_owner, station_id=station.id).get(
            transaction_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.data["results"]}
        assert tx.id in ids

    def test_list_company_owner_raises_fielderror_fail(
        self, auth_client, company_owner, company
    ):
        """Documents actual (buggy) behavior: `KhaznaTransaction` has no
        `company` field, so scoping the base queryset by `company` for a
        `CompanyOwner` raises `FieldError` instead of returning a scoped list."""
        with pytest.raises(FieldError):
            auth_client(company_owner, company_id=company.id).get(
                transaction_list_url()
            )

    def test_list_company_branch_manager_raises_fielderror_fail(
        self, auth_client, company_branch_manager, company
    ):
        with pytest.raises(FieldError):
            auth_client(company_branch_manager, company_id=company.id).get(
                transaction_list_url()
            )
