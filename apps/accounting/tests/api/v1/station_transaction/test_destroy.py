from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.utilities.testing import assert_soft_deleted, listed_ids

from .helpers import station_transaction_detail_url, station_transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionDestroy:
    @pytest.fixture(autouse=True)
    def setup(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        self.auth_client = auth_client
        self.admin = admin_user
        self.admin_client = auth_client(admin_user)
        self.station = station
        self.branch = branch
        self.create_transaction = station_transaction_factory

    def destroy(self, pk, client=None):
        return (client or self.admin_client).delete(station_transaction_detail_url(pk))

    def station_client(self, user):
        return self.auth_client(user, station_id=self.station.id)

    def test_destroy_unauthenticated_fail(self, api_client):
        tx = self.create_transaction()

        response = self.destroy(tx.id, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert StationKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_company_role_forbidden_fail(self, company_owner, company):
        tx = self.create_transaction()
        client = self.auth_client(company_owner, company_id=company.id)

        response = self.destroy(tx.id, client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_destroy_dashboard_user_success(self):
        tx = self.create_transaction()

        response = self.destroy(tx.id)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not StationKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_owner_can_delete_own_station_transaction_success(
        self, station_owner
    ):
        tx = self.create_transaction()

        response = self.destroy(tx.id, client=self.station_client(station_owner))

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_station_owner_cannot_delete_other_station_transaction_fail(
        self, station_owner, other_station, other_station_branch
    ):
        tx = self.create_transaction(
            station=other_station, station_branch=other_station_branch
        )

        response = self.destroy(tx.id, client=self.station_client(station_owner))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert StationKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_worker_cannot_delete_transaction_created_by_another_user_fail(
        self, station_worker
    ):
        tx = self.create_transaction(created_by=self.admin)

        response = self.destroy(tx.id, client=self.station_client(station_worker))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_does_not_reverse_balance_success(self):
        self.branch.balance = Decimal("50.00")
        self.branch.save(update_fields=["balance"])
        tx = self.create_transaction(status="approved", amount=Decimal("20.00"))

        response = self.destroy(tx.id)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("50.00")

    def test_destroy_finance_fail(self, finance_user):
        tx = self.create_transaction()

        response = self.destroy(tx.id, client=self.auth_client(finance_user))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert StationKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_customer_support_fail(self, customer_support_user):
        tx = self.create_transaction()

        response = self.destroy(tx.id, client=self.auth_client(customer_support_user))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert StationKhaznaTransaction.objects.filter(id=tx.id).exists()


class TestStationKhaznaTransactionSoftDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, station_transaction_factory):
        self.client = auth_client(admin_user)
        self.tx = station_transaction_factory()
        response = self.client.delete(station_transaction_detail_url(self.tx.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(StationKhaznaTransaction, self.tx.id)

    def test_deleted_transaction_hidden_from_list_success(self):
        response = self.client.get(station_transaction_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert self.tx.id not in listed_ids(response)

    def test_retrieve_deleted_transaction_not_found_fail(self):
        response = self.client.get(station_transaction_detail_url(self.tx.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_transaction_not_found_fail(self):
        response = self.client.delete(station_transaction_detail_url(self.tx.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND
