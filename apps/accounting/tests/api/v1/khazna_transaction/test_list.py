import pytest
from django.core.exceptions import FieldError
from rest_framework import status

from .helpers import transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {row["id"] for row in response.data["results"]}


class TestKhaznaTransactionList:
    """`KhaznaTransactionViewSet` is authenticated-only (`IsAuthenticated`) with
    no role permission restriction. Its `get_queryset` only special-cases
    `CompanyOwner`/`CompanyBranchManager`, and every other authenticated role
    (dashboard, station roles) receives the full, unscoped queryset."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, khazna_transaction_factory):
        self.auth_client = auth_client
        self.admin_client = auth_client(admin_user)
        self.create_transaction = khazna_transaction_factory
        self.url = transaction_list_url()

    def list(self, client=None):
        return (client or self.admin_client).get(self.url)

    def test_list_unauthenticated_fail(self, api_client):
        response = self.list(client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_dashboard_user_success(self):
        tx = self.create_transaction()

        response = self.list()

        assert response.status_code == status.HTTP_200_OK
        assert tx.id in returned_ids(response)

    def test_list_includes_rows_created_via_company_and_station_transactions_success(
        self, company_transaction_factory, station_transaction_factory
    ):
        company_tx = company_transaction_factory()
        station_tx = station_transaction_factory()

        response = self.list()

        ids = returned_ids(response)
        assert company_tx.id in ids
        assert station_tx.id in ids
        # The base serializer only exposes base-model fields.
        row = next(
            row for row in response.data["results"] if row["id"] == company_tx.id
        )
        assert "company" not in row
        assert "company_branch" not in row

    def test_list_station_owner_sees_unscoped_queryset_success(
        self, station_owner, station
    ):
        """Documents actual behavior: station roles are not filtered by
        `KhaznaTransactionViewSet.get_queryset`, so a station owner can see
        every khazna transaction in the system, not just their own."""
        tx = self.create_transaction()

        response = self.list(
            client=self.auth_client(station_owner, station_id=station.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert tx.id in returned_ids(response)

    def test_list_company_owner_raises_fielderror_fail(self, company_owner, company):
        """Documents actual (buggy) behavior: `KhaznaTransaction` has no
        `company` field, so scoping the base queryset by `company` for a
        `CompanyOwner` raises `FieldError` instead of returning a scoped list."""
        with pytest.raises(FieldError):
            self.list(client=self.auth_client(company_owner, company_id=company.id))

    def test_list_company_branch_manager_raises_fielderror_fail(
        self, company_branch_manager, company
    ):
        with pytest.raises(FieldError):
            self.list(
                client=self.auth_client(company_branch_manager, company_id=company.id)
            )
