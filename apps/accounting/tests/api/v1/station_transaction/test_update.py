from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.notifications.models import Notification

from .helpers import station_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionUpdate:
    def test_update_unauthenticated_fail(self, api_client, station_transaction_factory):
        tx = station_transaction_factory(status="pending")

        response = api_client.patch(
            station_transaction_detail_url(tx.id), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_company_role_forbidden_fail(
        self, auth_client, company_owner, company, station_transaction_factory
    ):
        tx = station_transaction_factory(status="pending")

        response = auth_client(company_owner, company_id=company.id).patch(
            station_transaction_detail_url(tx.id), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_not_found_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).patch(
            station_transaction_detail_url(999999),
            {"status": "approved"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_omitting_station_branch_raises_keyerror_fail(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        """Same actual (buggy) behavior as the company-side update
        serializer: a partial update that omits `station_branch` (e.g. the
        typical `{"status": "approved"}` approve payload) raises an
        unhandled `KeyError` instead of a clean validation error."""
        tx = station_transaction_factory(
            station=station, station_branch=branch, status="pending"
        )

        with pytest.raises(KeyError):
            auth_client(admin_user).patch(
                station_transaction_detail_url(tx.id),
                {"status": "approved"},
                format="json",
            )

    def test_update_full_payload_status_to_approved_success(
        self,
        auth_client,
        admin_user,
        station,
        branch,
        branch_manager,
        station_transaction_factory,
    ):
        branch.balance = Decimal("100.00")
        branch.save(update_fields=["balance"])
        tx = station_transaction_factory(
            station=station,
            station_branch=branch,
            status="pending",
            amount=Decimal("40.00"),
            is_incoming=True,
        )

        response = auth_client(admin_user).patch(
            station_transaction_detail_url(tx.id),
            {"station": station.id, "station_branch": branch.id, "status": "approved"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        branch.refresh_from_db()
        assert tx.status == StationKhaznaTransaction.TransactionStatus.APPROVED
        assert branch.balance == Decimal("60.00")
        notification = Notification.objects.get(user_id=branch_manager.id)
        assert notification.type == Notification.NotificationType.MONEY

    def test_update_already_approved_fail(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        tx = station_transaction_factory(
            station=station, station_branch=branch, status="approved"
        )

        response = auth_client(admin_user).patch(
            station_transaction_detail_url(tx.id),
            {"station": station.id, "station_branch": branch.id, "status": "declined"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "لا يمكن اتمام عملية هيا منهيه بالفعل"

    def test_update_station_branch_mismatch_fail(
        self,
        auth_client,
        admin_user,
        station,
        branch,
        other_station_branch,
        station_transaction_factory,
    ):
        tx = station_transaction_factory(
            station=station, station_branch=branch, status="pending"
        )

        response = auth_client(admin_user).patch(
            station_transaction_detail_url(tx.id),
            {
                "station": station.id,
                "station_branch": other_station_branch.id,
                "status": "approved",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "المحطة غير مطابقة للفرع"

    def test_update_station_owner_cannot_update_other_station_transaction_fail(
        self,
        auth_client,
        station_owner,
        station,
        other_station,
        other_station_branch,
        station_transaction_factory,
    ):
        tx = station_transaction_factory(
            station=other_station, station_branch=other_station_branch, status="pending"
        )

        response = auth_client(station_owner, station_id=station.id).patch(
            station_transaction_detail_url(tx.id),
            {
                "station": other_station.id,
                "station_branch": other_station_branch.id,
                "status": "approved",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
