from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import (
    operation_detail_url,
    set_balance,
)
from apps.notifications.models import Notification


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def update_payload(operation, **overrides):
    payload = {
        "car": operation.car_id,
        "station_branch": operation.station_branch_id,
        "service": operation.service_id,
        "car_meter": "100.00",
        "status": CarOperation.OperationStatus.COMPLETED,
    }
    payload.update(overrides)
    return payload


def test_partial_update_without_authentication_fail(api_client, car_operation_factory):
    operation = car_operation_factory()

    response = api_client.patch(
        operation_detail_url(operation.id),
        update_payload(operation),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_partial_update_complete_as_station_worker_success(
    auth_client,
    station_worker,
    station,
    station_owner,
    branch_manager,
    company_owner,
    company_branch_manager,
    company,
    branch,
    car_operation_factory,
):
    set_balance(branch, "500.00")
    operation = car_operation_factory(
        status=CarOperation.OperationStatus.PENDING,
        company_cost=Decimal("100.00"),
        station_cost=Decimal("80.00"),
        amount=Decimal("10.00"),
    )

    response = auth_client(station_worker, station_id=station.id).patch(
        operation_detail_url(operation.id),
        update_payload(operation),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    operation.refresh_from_db()
    branch.refresh_from_db()
    assert operation.status == CarOperation.OperationStatus.COMPLETED
    assert response.data["status"] == CarOperation.OperationStatus.COMPLETED
    assert response.data["car"] == operation.car_id
    assert response.data["amount"] == "10.00"
    assert response.data["company_cost"] == "100.00"
    assert response.data["station_cost"] == "80.00"
    assert branch.balance == Decimal("420.00")

    company_txn = CompanyKhaznaTransaction.objects.get()
    assert company_txn.company_id == operation.car.branch.company_id
    assert company_txn.company_branch_id == operation.car.branch_id
    assert company_txn.amount == Decimal("100.00")
    assert company_txn.is_internal is True
    assert company_txn.created_by_id == station_worker.id
    assert operation.car.plate in company_txn.description

    station_txn = StationKhaznaTransaction.objects.get()
    assert station_txn.station_id == branch.station_id
    assert station_txn.station_branch_id == branch.id
    assert station_txn.amount == Decimal("80.00")
    assert station_txn.is_internal is False
    assert station_txn.created_by_id == station_worker.id

    money_user_ids = set(
        Notification.objects.filter(
            type=Notification.NotificationType.MONEY
        ).values_list("user_id", flat=True)
    )
    assert station_worker.id in money_user_ids
    assert station_owner.id in money_user_ids
    assert branch_manager.id in money_user_ids
    assert company_owner.id in money_user_ids
    assert company_branch_manager.id in money_user_ids


@pytest.mark.parametrize("role_fixture", ["company_owner", "admin_user"])
def test_partial_update_complete_allowed_roles_success(
    role_fixture,
    request,
    auth_client,
    company,
    station,
    company_owner,
    car_operation_factory,
    branch,
):
    user = request.getfixturevalue(role_fixture)
    set_balance(branch, "200.00")
    operation = car_operation_factory(
        status=CarOperation.OperationStatus.IN_PROGRESS,
        company_cost=Decimal("50.00"),
        station_cost=Decimal("40.00"),
    )
    client_kwargs = {}
    if role_fixture == "company_owner":
        client_kwargs["company_id"] = company.id

    response = auth_client(user, **client_kwargs).patch(
        operation_detail_url(operation.id),
        update_payload(operation),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    operation.refresh_from_db()
    assert operation.status == CarOperation.OperationStatus.COMPLETED
    assert StationKhaznaTransaction.objects.count() == 1
    assert CompanyKhaznaTransaction.objects.count() == 1


def test_partial_update_cancel_does_not_create_transactions_success(
    auth_client,
    company_owner,
    company,
    car_operation_factory,
    branch,
):
    set_balance(branch, "200.00")
    operation = car_operation_factory(status=CarOperation.OperationStatus.PENDING)

    response = auth_client(company_owner, company_id=company.id).patch(
        operation_detail_url(operation.id),
        update_payload(operation, status=CarOperation.OperationStatus.CANCELLED),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    operation.refresh_from_db()
    branch.refresh_from_db()
    assert operation.status == CarOperation.OperationStatus.CANCELLED
    assert response.data["status"] == CarOperation.OperationStatus.CANCELLED
    assert branch.balance == Decimal("200.00")
    assert CompanyKhaznaTransaction.objects.count() == 0
    assert StationKhaznaTransaction.objects.count() == 0


@pytest.mark.parametrize(
    "operation_status",
    [
        CarOperation.OperationStatus.COMPLETED,
        CarOperation.OperationStatus.CANCELLED,
    ],
)
def test_partial_update_finished_operation_fail(
    operation_status,
    auth_client,
    company_owner,
    company,
    car_operation_factory,
):
    operation = car_operation_factory(status=operation_status)

    response = auth_client(company_owner, company_id=company.id).patch(
        operation_detail_url(operation.id),
        update_payload(operation, status=CarOperation.OperationStatus.PENDING),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    operation.refresh_from_db()
    assert operation.status == operation_status


def test_partial_update_car_meter_below_last_meter_fail(
    auth_client,
    company_owner,
    company,
    company_car,
    car_operation_factory,
):
    company_car.last_meter = 500
    company_car.save(update_fields=["last_meter"])
    operation = car_operation_factory()

    response = auth_client(company_owner, company_id=company.id).patch(
        operation_detail_url(operation.id),
        update_payload(operation, car_meter="100.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    operation.refresh_from_db()
    assert operation.status == CarOperation.OperationStatus.PENDING


def test_partial_update_other_company_as_owner_fail(
    auth_client,
    company_owner,
    company,
    car_factory,
    driver_factory,
    other_company_branch,
    car_operation_factory,
):
    operation = car_operation_factory(
        car=car_factory(branch=other_company_branch),
        driver=driver_factory(branch=other_company_branch),
    )

    response = auth_client(company_owner, company_id=company.id).patch(
        operation_detail_url(operation.id),
        update_payload(operation),
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
