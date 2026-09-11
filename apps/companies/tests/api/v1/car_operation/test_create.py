from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_models import Car
from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import (
    operation_list_url,
    set_balance,
)
from apps.notifications.models import Notification


pytestmark = [pytest.mark.api, pytest.mark.django_db]

HOLDERS = [
    (Car.BalanceSource.BRANCH, "company_branch"),
    (Car.BalanceSource.COMPANY, "company"),
]


class TestCarOperationCreate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, company_car, car_operation_payload_factory):
        self.admin = admin_user
        self.car = company_car
        self.build_payload = car_operation_payload_factory
        self.client = auth_client(admin_user)
        self.url = operation_list_url()
        set_balance(company_car, "1000.00")

    def create(self, payload=None, client=None):
        return (client or self.client).post(
            self.url, self.build_payload() if payload is None else payload, format="json"
        )

    def fund_holder(self, request, balance_source, holder_fixture, **balances):
        """Point the car at a holder and set every balance in the chain."""
        holder = request.getfixturevalue(holder_fixture)
        self.car.balance_source = balance_source
        self.car.save(update_fields=["balance_source"])
        set_balance(self.car, balances.get("car", "0.00"))
        set_balance(request.getfixturevalue("company"), balances.get("company", "0.00"))
        set_balance(
            request.getfixturevalue("company_branch"), balances.get("branch", "0.00")
        )
        set_balance(holder, balances.get("holder", "1000.00"))
        return holder

    def test_create_without_authentication_fail(self, api_client):
        response = self.create(client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CarOperation.objects.count() == 0

    @pytest.mark.parametrize(
        "role_fixture",
        ["company_owner", "company_branch_manager", "station_worker", "station_owner"],
    )
    def test_create_forbidden_role_fail(
        self, role_fixture, request, auth_client, company, station
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture in {"company_owner", "company_branch_manager"}:
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_worker", "station_owner"}:
            client_kwargs["station_id"] = station.id

        response = self.create(client=auth_client(user, **client_kwargs))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CarOperation.objects.count() == 0

    def test_create_pending_as_admin_deducts_car_balance_success(
        self, company_driver, branch, station_worker, service
    ):
        start = timezone.now()
        payload = self.build_payload(
            start_time=start.isoformat(),
            end_time=(start + timedelta(minutes=5)).isoformat(),
            status=CarOperation.OperationStatus.PENDING,
        )

        response = self.create(payload)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CarOperation.objects.get()
        self.car.refresh_from_db()
        assert response.data["car"] == self.car.id
        assert response.data["driver"] == company_driver.id
        assert response.data["station_branch"] == branch.id
        assert response.data["worker"] == station_worker.id
        assert "service" not in response.data
        assert response.data["amount"] == "10.00"
        assert response.data["car_meter"] == "100.00"
        assert response.data["status"] == CarOperation.OperationStatus.PENDING
        assert response.data["cost"] == "100.00"
        assert response.data["company_cost"] == "100.00"
        assert response.data["station_cost"] == "100.00"
        assert response.data["profits"] == "0.00"
        assert response.data["unit"] == service.unit
        assert response.data["fuel_type"] == payload["fuel_type"]
        assert created.car_id == self.car.id
        assert created.driver_id == company_driver.id
        assert created.station_branch_id == branch.id
        assert created.worker_id == station_worker.id
        assert created.service_id == service.id
        assert created.amount == Decimal("10.00")
        assert created.cost == Decimal("100.00")
        assert created.company_cost == Decimal("100.00")
        assert created.station_cost == Decimal("100.00")
        assert created.profits == Decimal("0.00")
        assert created.unit == service.unit
        assert created.duration == 300
        assert created.code
        assert created.created_by_id == self.admin.id
        assert created.car_first_meter == Decimal("100.00")
        assert self.car.balance == Decimal("900.00")
        assert self.car.last_meter == 100
        assert self.car.fuel_consumption_rate == 10
        assert CompanyKhaznaTransaction.objects.count() == 0
        assert StationKhaznaTransaction.objects.count() == 0

    def test_create_completed_creates_transactions_and_notifications_success(
        self,
        company_owner,
        company_branch_manager,
        station_owner,
        branch_manager,
        station_worker,
        branch,
    ):
        set_balance(branch, "500.00")

        response = self.create(
            self.build_payload(status=CarOperation.OperationStatus.COMPLETED)
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CarOperation.objects.get()
        self.car.refresh_from_db()
        branch.refresh_from_db()
        assert created.status == CarOperation.OperationStatus.COMPLETED
        assert created.company_cost == Decimal("100.00")
        assert created.station_cost == Decimal("100.00")
        assert self.car.balance == Decimal("900.00")
        assert branch.balance == Decimal("400.00")

        company_txn = CompanyKhaznaTransaction.objects.get()
        assert company_txn.company_id == self.car.branch.company_id
        assert company_txn.company_branch_id == self.car.branch_id
        assert company_txn.amount == Decimal("100.00")
        assert company_txn.is_internal is True
        assert company_txn.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED
        assert company_txn.created_by_id == self.admin.id
        assert self.car.plate in company_txn.description

        station_txn = StationKhaznaTransaction.objects.get()
        assert station_txn.station_id == branch.station_id
        assert station_txn.station_branch_id == branch.id
        assert station_txn.amount == Decimal("100.00")
        assert station_txn.is_internal is False
        assert station_txn.status == StationKhaznaTransaction.TransactionStatus.APPROVED
        assert station_txn.created_by_id == station_worker.id

        money_user_ids = set(
            Notification.objects.filter(
                type=Notification.NotificationType.MONEY
            ).values_list("user_id", flat=True)
        )
        assert company_owner.id in money_user_ids
        assert company_branch_manager.id in money_user_ids
        assert station_owner.id in money_user_ids
        assert branch_manager.id in money_user_ids
        assert station_worker.id in money_user_ids

    def test_create_with_company_fees_success(self, company_branch):
        company_branch.fees = Decimal("10.00")
        company_branch.save(update_fields=["fees"])

        response = self.create()

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CarOperation.objects.get()
        self.car.refresh_from_db()
        assert created.cost == Decimal("100.00")
        assert created.company_cost == Decimal("110.00")
        assert created.station_cost == Decimal("100.00")
        assert created.profits == Decimal("10.00")
        assert self.car.balance == Decimal("890.00")
        assert response.data["company_cost"] == "110.00"
        assert response.data["profits"] == "10.00"

    def test_create_amount_above_available_liters_fail(self):
        set_balance(self.car, "100.00")

        response = self.create(self.build_payload(amount="11.00"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CarOperation.objects.count() == 0
        self.car.refresh_from_db()
        assert self.car.balance == Decimal("100.00")

    def test_create_car_meter_below_last_meter_fail(self):
        self.car.last_meter = 200
        self.car.save(update_fields=["last_meter"])

        response = self.create(self.build_payload(car_meter="100.00"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CarOperation.objects.count() == 0

    @pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
    def test_create_as_dashboard_role_success(self, role_fixture, request, auth_client):
        user = request.getfixturevalue(role_fixture)

        response = self.create(client=auth_client(user))

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CarOperation.objects.get()
        assert created.created_by_id == user.id
        assert created.amount == Decimal("10.00")

    @pytest.mark.parametrize(
        "payload",
        [
            {"amount": "10.00", "car_meter": "100.00"},
            {"car": 1, "amount": "10.00"},
        ],
    )
    def test_create_missing_required_fields_fail(self, payload):
        if payload.get("car") == 1:
            payload = {**payload, "car": self.car.id}

        response = self.create(payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CarOperation.objects.count() == 0

    @pytest.mark.parametrize(("balance_source", "holder_fixture"), HOLDERS)
    def test_create_deducts_from_the_configured_holder_success(
        self, balance_source, holder_fixture, request
    ):
        holder = self.fund_holder(request, balance_source, holder_fixture)

        response = self.create()

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CarOperation.objects.get()
        self.car.refresh_from_db()
        holder.refresh_from_db()
        assert created.company_cost == Decimal("100.00")
        assert self.car.balance == Decimal("0.00")
        assert holder.balance == Decimal("900.00")

    @pytest.mark.parametrize(("balance_source", "holder_fixture"), HOLDERS)
    def test_create_leaves_the_other_balances_untouched_success(
        self, balance_source, holder_fixture, request, company, company_branch
    ):
        self.fund_holder(
            request,
            balance_source,
            holder_fixture,
            car="500.00",
            company="1000.00",
            branch="1000.00",
            holder="1000.00",
        )

        response = self.create()

        assert response.status_code == status.HTTP_201_CREATED, response.data
        self.car.refresh_from_db()
        company.refresh_from_db()
        company_branch.refresh_from_db()
        assert self.car.balance == Decimal("500.00")
        if balance_source == Car.BalanceSource.BRANCH:
            assert company_branch.balance == Decimal("900.00")
            assert company.balance == Decimal("1000.00")
        else:
            assert company.balance == Decimal("900.00")
            assert company_branch.balance == Decimal("1000.00")

    @pytest.mark.parametrize(("balance_source", "holder_fixture"), HOLDERS)
    def test_create_above_holder_balance_fail(
        self, balance_source, holder_fixture, request
    ):
        holder = self.fund_holder(
            request, balance_source, holder_fixture, car="5000.00", holder="50.00"
        )

        response = self.create()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CarOperation.objects.count() == 0
        holder.refresh_from_db()
        self.car.refresh_from_db()
        assert holder.balance == Decimal("50.00")
        assert self.car.balance == Decimal("5000.00")
