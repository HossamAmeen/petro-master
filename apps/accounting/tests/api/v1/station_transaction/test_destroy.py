from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction

from .helpers import station_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionDestroy:
    def test_destroy_unauthenticated_fail(self, api_client, station_transaction_factory):
        tx = station_transaction_factory()

        response = api_client.delete(station_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert StationKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_company_role_forbidden_fail(
        self, auth_client, company_owner, company, station_transaction_factory
    ):
        tx = station_transaction_factory()

        response = auth_client(company_owner, company_id=company.id).delete(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_destroy_dashboard_user_success(
        self, auth_client, admin_user, station_transaction_factory
    ):
        tx = station_transaction_factory()

        response = auth_client(admin_user).delete(station_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not StationKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_owner_can_delete_own_station_transaction_success(
        self, auth_client, station_owner, station, branch, station_transaction_factory
    ):
        tx = station_transaction_factory(station=station, station_branch=branch)

        response = auth_client(station_owner, station_id=station.id).delete(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_station_owner_cannot_delete_other_station_transaction_fail(
        self,
        auth_client,
        station_owner,
        station,
        other_station,
        other_station_branch,
        station_transaction_factory,
    ):
        tx = station_transaction_factory(
            station=other_station, station_branch=other_station_branch
        )

        response = auth_client(station_owner, station_id=station.id).delete(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert StationKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_worker_cannot_delete_transaction_created_by_another_user_fail(
        self,
        auth_client,
        station_worker,
        station,
        branch,
        admin_user,
        station_transaction_factory,
    ):
        tx = station_transaction_factory(
            station=station, station_branch=branch, created_by=admin_user
        )

        response = auth_client(station_worker, station_id=station.id).delete(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_does_not_reverse_balance_success(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        branch.balance = Decimal("50.00")
        branch.save(update_fields=["balance"])
        tx = station_transaction_factory(
            station=station,
            station_branch=branch,
            status="approved",
            amount=Decimal("20.00"),
        )

        response = auth_client(admin_user).delete(station_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        branch.refresh_from_db()
        assert branch.balance == Decimal("50.00")
