from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import (
    operation_list_url,
    set_balance,
)
from apps.notifications.models import Notification


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_create_without_authentication_fail(api_client, car_operation_payload_factory):
    response = api_client.post(
        operation_list_url(),
        car_operation_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert CarOperation.objects.count() == 0


@pytest.mark.parametrize(
    "role_fixture",
    ["company_owner", "company_branch_manager", "station_worker", "station_owner"],
)
def test_create_forbidden_role_fail(
    role_fixture,
    request,
    auth_client,
    company,
    station,
    car_operation_payload_factory,
    company_car,
):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture in {"company_owner", "company_branch_manager"}:
        client_kwargs["company_id"] = company.id
    if role_fixture in {"station_worker", "station_owner"}:
        client_kwargs["station_id"] = station.id
    set_balance(company_car, "1000.00")

    response = auth_client(user, **client_kwargs).post(
        operation_list_url(),
        car_operation_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert CarOperation.objects.count() == 0


def test_create_pending_as_admin_deducts_car_balance_success(
    auth_client,
    admin_user,
    company_car,
    company_driver,
    branch,
    station_worker,
    service,
    car_operation_payload_factory,
):
    set_balance(company_car, "1000.00")
    start = timezone.now()
    payload = car_operation_payload_factory(
        start_time=start.isoformat(),
        end_time=(start + timedelta(minutes=5)).isoformat(),
        status=CarOperation.OperationStatus.PENDING,
    )

    response = auth_client(admin_user).post(
        operation_list_url(), payload, format="json"
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CarOperation.objects.get()
    company_car.refresh_from_db()
    assert response.data["car"] == company_car.id
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
    assert created.car_id == company_car.id
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
    assert created.created_by_id == admin_user.id
    assert created.car_first_meter == Decimal("100.00")
    assert company_car.balance == Decimal("900.00")
    assert company_car.last_meter == 100
    assert company_car.fuel_consumption_rate == 10
    assert CompanyKhaznaTransaction.objects.count() == 0
    assert StationKhaznaTransaction.objects.count() == 0


def test_create_completed_creates_transactions_and_notifications_success(
    auth_client,
    admin_user,
    company_owner,
    company_branch_manager,
    station_owner,
    branch_manager,
    station_worker,
    company_car,
    branch,
    car_operation_payload_factory,
):
    set_balance(company_car, "1000.00")
    set_balance(branch, "500.00")
    payload = car_operation_payload_factory(
        status=CarOperation.OperationStatus.COMPLETED
    )

    response = auth_client(admin_user).post(
        operation_list_url(), payload, format="json"
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CarOperation.objects.get()
    company_car.refresh_from_db()
    branch.refresh_from_db()
    assert created.status == CarOperation.OperationStatus.COMPLETED
    assert created.company_cost == Decimal("100.00")
    assert created.station_cost == Decimal("100.00")
    assert company_car.balance == Decimal("900.00")
    assert branch.balance == Decimal("400.00")

    company_txn = CompanyKhaznaTransaction.objects.get()
    assert company_txn.company_id == company_car.branch.company_id
    assert company_txn.company_branch_id == company_car.branch_id
    assert company_txn.amount == Decimal("100.00")
    assert company_txn.is_internal is True
    assert company_txn.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED
    assert company_txn.created_by_id == admin_user.id
    assert company_car.plate in company_txn.description

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


def test_create_with_company_fees_success(
    auth_client,
    admin_user,
    company_car,
    company_branch,
    car_operation_payload_factory,
):
    company_branch.fees = Decimal("10.00")
    company_branch.save(update_fields=["fees"])
    set_balance(company_car, "1000.00")

    response = auth_client(admin_user).post(
        operation_list_url(),
        car_operation_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CarOperation.objects.get()
    company_car.refresh_from_db()
    assert created.cost == Decimal("100.00")
    assert created.company_cost == Decimal("110.00")
    assert created.station_cost == Decimal("100.00")
    assert created.profits == Decimal("10.00")
    assert company_car.balance == Decimal("890.00")
    assert response.data["company_cost"] == "110.00"
    assert response.data["profits"] == "10.00"


def test_create_amount_above_available_liters_fail(
    auth_client,
    admin_user,
    company_car,
    car_operation_payload_factory,
):
    set_balance(company_car, "100.00")

    response = auth_client(admin_user).post(
        operation_list_url(),
        car_operation_payload_factory(amount="11.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CarOperation.objects.count() == 0
    company_car.refresh_from_db()
    assert company_car.balance == Decimal("100.00")


def test_create_car_meter_below_last_meter_fail(
    auth_client,
    admin_user,
    company_car,
    car_operation_payload_factory,
):
    company_car.last_meter = 200
    company_car.save(update_fields=["last_meter"])
    set_balance(company_car, "1000.00")

    response = auth_client(admin_user).post(
        operation_list_url(),
        car_operation_payload_factory(car_meter="100.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CarOperation.objects.count() == 0


@pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
def test_create_as_dashboard_role_success(
    role_fixture,
    request,
    auth_client,
    company_car,
    car_operation_payload_factory,
):
    user = request.getfixturevalue(role_fixture)
    set_balance(company_car, "1000.00")

    response = auth_client(user).post(
        operation_list_url(),
        car_operation_payload_factory(),
        format="json",
    )

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
def test_create_missing_required_fields_fail(
    payload,
    auth_client,
    admin_user,
    company_car,
    car_operation_payload_factory,
):
    set_balance(company_car, "1000.00")
    if payload.get("car") == 1:
        payload = {**payload, "car": company_car.id}

    response = auth_client(admin_user).post(
        operation_list_url(), payload, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CarOperation.objects.count() == 0
