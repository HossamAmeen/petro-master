from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.notifications.models import Notification

from .helpers import create_payload, station_transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionCreate:
    def test_create_unauthenticated_fail(self, api_client, station, branch):
        response = api_client.post(
            station_transaction_list_url(),
            create_payload(station, branch),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_company_role_forbidden_fail(
        self, auth_client, company_owner, company, station, branch
    ):
        response = auth_client(company_owner, company_id=company.id).post(
            station_transaction_list_url(),
            create_payload(station, branch),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_dashboard_user_success(
        self, auth_client, admin_user, station, branch
    ):
        response = auth_client(admin_user).post(
            station_transaction_list_url(),
            create_payload(station, branch),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        tx = StationKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.station_id == station.id
        assert tx.station_branch_id == branch.id

    def test_create_station_owner_success(
        self, auth_client, station_owner, station, branch
    ):
        response = auth_client(station_owner, station_id=station.id).post(
            station_transaction_list_url(),
            create_payload(station, branch),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_station_worker_success(
        self, auth_client, station_worker, station, branch
    ):
        response = auth_client(station_worker, station_id=station.id).post(
            station_transaction_list_url(),
            create_payload(station, branch),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_missing_station_branch_raises_keyerror_fail(
        self, auth_client, admin_user, station, branch
    ):
        """Documents actual (buggy) behavior: unlike the company create
        serializer, `station_branch` is not redeclared as `required=True`
        here (the model field is `blank=True`), so DRF treats it as optional.
        Omitting it leaves `attrs` without a `station_branch` key, and
        `validate()` indexes it unconditionally, raising an unhandled
        `KeyError` instead of returning a clean validation error."""
        payload = create_payload(station, branch)
        payload.pop("station_branch")

        with pytest.raises(KeyError):
            auth_client(admin_user).post(
                station_transaction_list_url(), payload, format="json"
            )

    def test_create_station_branch_mismatch_fail(
        self, auth_client, admin_user, station, other_station_branch
    ):
        response = auth_client(admin_user).post(
            station_transaction_list_url(),
            create_payload(station, other_station_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "المحطة غير مطابقة للفرع"

    def test_create_missing_amount_fail(self, auth_client, admin_user, station, branch):
        payload = create_payload(station, branch)
        payload.pop("amount")

        response = auth_client(admin_user).post(
            station_transaction_list_url(), payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "amount"

    def test_create_ignores_client_supplied_reference_code_success(
        self, auth_client, admin_user, station, branch
    ):
        response = auth_client(admin_user).post(
            station_transaction_list_url(),
            create_payload(station, branch, reference_code="CLIENT-SET"),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        tx = StationKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.reference_code != "CLIENT-SET"

    def test_create_ignores_client_supplied_created_by_success(
        self, auth_client, admin_user, finance_user, station, branch
    ):
        response = auth_client(admin_user).post(
            station_transaction_list_url(),
            create_payload(station, branch, created_by=finance_user.id),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        tx = StationKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.created_by_id == admin_user.id

    def test_create_pending_does_not_touch_balance_or_notify_success(
        self, auth_client, admin_user, station, branch
    ):
        branch.balance = Decimal("100.00")
        branch.save(update_fields=["balance"])
        notifications_before = Notification.objects.count()

        response = auth_client(admin_user).post(
            station_transaction_list_url(),
            create_payload(station, branch, status="pending", amount="10.00"),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        branch.refresh_from_db()
        assert branch.balance == Decimal("100.00")
        assert Notification.objects.count() == notifications_before

    def test_create_approved_deducts_branch_balance_and_notifies_manager_success(
        self, auth_client, admin_user, station, branch, branch_manager
    ):
        branch.balance = Decimal("100.00")
        branch.save(update_fields=["balance"])

        response = auth_client(admin_user).post(
            station_transaction_list_url(),
            create_payload(
                station, branch, status="approved", is_incoming=True, amount="30.00"
            ),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        branch.refresh_from_db()
        assert branch.balance == Decimal("70.00")
        notification = Notification.objects.get(user_id=branch_manager.id)
        assert notification.type == Notification.NotificationType.MONEY
        assert branch.name in notification.title

    def test_create_approved_outgoing_credits_branch_balance_success(
        self, auth_client, admin_user, station, branch
    ):
        branch.balance = Decimal("100.00")
        branch.save(update_fields=["balance"])

        response = auth_client(admin_user).post(
            station_transaction_list_url(),
            create_payload(
                station, branch, status="approved", is_incoming=False, amount="30.00"
            ),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        branch.refresh_from_db()
        assert branch.balance == Decimal("130.00")
