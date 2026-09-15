from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.notifications.models import Notification

from .helpers import create_payload, station_transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionCreate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, station, branch):
        self.auth_client = auth_client
        self.admin = admin_user
        self.admin_client = auth_client(admin_user)
        self.station = station
        self.branch = branch
        self.url = station_transaction_list_url()

    def create(self, client=None, payload=None, **overrides):
        if payload is None:
            payload = create_payload(self.station, self.branch, **overrides)
        return (client or self.admin_client).post(self.url, payload, format="json")

    def set_branch_balance(self, amount):
        self.branch.balance = Decimal(amount)
        self.branch.save(update_fields=["balance"])

    def test_create_unauthenticated_fail(self, api_client):
        response = self.create(client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_company_role_forbidden_fail(self, company_owner, company):
        client = self.auth_client(company_owner, company_id=company.id)

        response = self.create(client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_dashboard_user_success(self):
        response = self.create()

        assert response.status_code == status.HTTP_201_CREATED
        tx = StationKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.station_id == self.station.id
        assert tx.station_branch_id == self.branch.id

    def test_create_station_owner_success(self, station_owner):
        client = self.auth_client(station_owner, station_id=self.station.id)

        response = self.create(client=client)

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_station_worker_success(self, station_worker):
        client = self.auth_client(station_worker, station_id=self.station.id)

        response = self.create(client=client)

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_missing_station_branch_raises_keyerror_fail(self):
        """Documents actual (buggy) behavior: unlike the company create
        serializer, `station_branch` is not redeclared as `required=True`
        here (the model field is `blank=True`), so DRF treats it as optional.
        Omitting it leaves `attrs` without a `station_branch` key, and
        `validate()` indexes it unconditionally, raising an unhandled
        `KeyError` instead of returning a clean validation error."""
        payload = create_payload(self.station, self.branch)
        payload.pop("station_branch")

        with pytest.raises(KeyError):
            self.create(payload=payload)

    def test_create_station_branch_mismatch_fail(self, other_station_branch):
        response = self.create(
            payload=create_payload(self.station, other_station_branch)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "المحطة غير مطابقة للفرع"

    def test_create_missing_amount_fail(self):
        payload = create_payload(self.station, self.branch)
        payload.pop("amount")

        response = self.create(payload=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "amount"

    def test_create_ignores_client_supplied_reference_code_success(self):
        response = self.create(reference_code="CLIENT-SET")

        assert response.status_code == status.HTTP_201_CREATED
        tx = StationKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.reference_code != "CLIENT-SET"

    def test_create_ignores_client_supplied_created_by_success(self, finance_user):
        response = self.create(created_by=finance_user.id)

        assert response.status_code == status.HTTP_201_CREATED
        tx = StationKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.created_by_id == self.admin.id

    def test_create_pending_does_not_touch_balance_or_notify_success(self):
        self.set_branch_balance("100.00")
        notifications_before = Notification.objects.count()

        response = self.create(status="pending", amount="10.00")

        assert response.status_code == status.HTTP_201_CREATED
        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("100.00")
        assert Notification.objects.count() == notifications_before

    def test_create_approved_deducts_branch_balance_and_notifies_manager_success(
        self, branch_manager
    ):
        self.set_branch_balance("100.00")

        response = self.create(status="approved", is_incoming=True, amount="30.00")

        assert response.status_code == status.HTTP_201_CREATED
        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("70.00")
        notification = Notification.objects.get(user_id=branch_manager.id)
        assert notification.type == Notification.NotificationType.MONEY
        assert self.branch.name in notification.title

    def test_create_approved_outgoing_credits_branch_balance_success(self):
        self.set_branch_balance("100.00")

        response = self.create(status="approved", is_incoming=False, amount="30.00")

        assert response.status_code == status.HTTP_201_CREATED
        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("130.00")

    def test_create_finance_success(self, finance_user):
        response = self.create(client=self.auth_client(finance_user))

        assert response.status_code == status.HTTP_201_CREATED
        tx = StationKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.created_by_id == finance_user.id

    def test_create_customer_support_fail(self, customer_support_user):
        self.set_branch_balance("100.00")
        client = self.auth_client(customer_support_user)

        response = self.create(client=client, status="approved", amount="40.00")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not StationKhaznaTransaction.objects.exists()
        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("100.00")
        assert not Notification.objects.exists()
