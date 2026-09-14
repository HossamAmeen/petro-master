from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.notifications.models import Notification

from .helpers import station_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionUpdate:
    @pytest.fixture(autouse=True)
    def setup(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        self.auth_client = auth_client
        self.admin_client = auth_client(admin_user)
        self.station = station
        self.branch = branch
        self.create_transaction = station_transaction_factory

    def update(self, pk, payload, client=None):
        return (client or self.admin_client).patch(
            station_transaction_detail_url(pk), payload, format="json"
        )

    def full_payload(self, status, station_branch=None):
        return {
            "station": self.station.id,
            "station_branch": (station_branch or self.branch).id,
            "status": status,
        }

    def test_update_unauthenticated_fail(self, api_client):
        tx = self.create_transaction(status="pending")

        response = self.update(tx.id, {"status": "approved"}, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_company_role_forbidden_fail(self, company_owner, company):
        tx = self.create_transaction(status="pending")
        client = self.auth_client(company_owner, company_id=company.id)

        response = self.update(tx.id, {"status": "approved"}, client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_not_found_fail(self):
        response = self.update(999999, {"status": "approved"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_omitting_station_branch_raises_keyerror_fail(self):
        """Same actual (buggy) behavior as the company-side update
        serializer: a partial update that omits `station_branch` (e.g. the
        typical `{"status": "approved"}` approve payload) raises an
        unhandled `KeyError` instead of a clean validation error."""
        tx = self.create_transaction(status="pending")

        with pytest.raises(KeyError):
            self.update(tx.id, {"status": "approved"})

    def test_update_full_payload_status_to_approved_success(self, branch_manager):
        self.branch.balance = Decimal("100.00")
        self.branch.save(update_fields=["balance"])
        tx = self.create_transaction(
            status="pending", amount=Decimal("40.00"), is_incoming=True
        )

        response = self.update(tx.id, self.full_payload("approved"))

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        self.branch.refresh_from_db()
        assert tx.status == StationKhaznaTransaction.TransactionStatus.APPROVED
        assert self.branch.balance == Decimal("60.00")
        notification = Notification.objects.get(user_id=branch_manager.id)
        assert notification.type == Notification.NotificationType.MONEY

    def test_update_already_approved_fail(self):
        tx = self.create_transaction(status="approved")

        response = self.update(tx.id, self.full_payload("declined"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "لا يمكن اتمام عملية هيا منهيه بالفعل"

    def test_update_station_branch_mismatch_fail(self, other_station_branch):
        tx = self.create_transaction(status="pending")

        response = self.update(
            tx.id, self.full_payload("approved", station_branch=other_station_branch)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "المحطة غير مطابقة للفرع"

    def test_update_station_owner_cannot_update_other_station_transaction_fail(
        self, station_owner, other_station, other_station_branch
    ):
        tx = self.create_transaction(
            station=other_station, station_branch=other_station_branch, status="pending"
        )
        client = self.auth_client(station_owner, station_id=self.station.id)

        response = self.update(
            tx.id,
            {
                "station": other_station.id,
                "station_branch": other_station_branch.id,
                "status": "approved",
            },
            client=client,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_status_to_declined_does_not_touch_balance_or_notify_success(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        branch.balance = Decimal("100.00")
        branch.save(update_fields=["balance"])
        tx = station_transaction_factory(
            station=station, station_branch=branch, status="pending"
        )

        response = auth_client(admin_user).patch(
            station_transaction_detail_url(tx.id),
            {
                "station": station.id,
                "station_branch": branch.id,
                "status": "declined",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        tx.refresh_from_db()
        branch.refresh_from_db()
        assert tx.status == StationKhaznaTransaction.TransactionStatus.DECLINED
        assert tx.updated_by_id == admin_user.id
        assert branch.balance == Decimal("100.00")
        assert not Notification.objects.exists()

    def test_put_uses_read_serializer_and_rejects_nested_station_fail(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        """PUT is not handled by `get_serializer_class`, so it falls back to the
        read serializer whose nested `station` field only accepts objects. The
        request is rejected and the transaction is left unchanged."""
        tx = station_transaction_factory(
            station=station, station_branch=branch, status="approved"
        )

        response = auth_client(admin_user).put(
            station_transaction_detail_url(tx.id),
            {
                "station": station.id,
                "amount": "999.00",
                "reference_code": tx.reference_code,
                "created_by": admin_user.id,
                "status": "pending",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "station"
        tx.refresh_from_db()
        assert tx.amount == Decimal("10.00")
        assert tx.status == StationKhaznaTransaction.TransactionStatus.APPROVED
