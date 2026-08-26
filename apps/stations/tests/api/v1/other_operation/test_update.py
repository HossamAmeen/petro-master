from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.operation_model import CarOperation
from apps.notifications.models import Notification
from apps.stations.tests.helpers import (
    image_file,
    notification_user_ids,
    other_costs,
    other_url,
    set_balance,
    worker_client,
)


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def configure_other_money(company_branch, branch, car, station, **overrides):
    company_branch.other_service_fees = Decimal(
        overrides.get("company_fees", "10.00")
    )
    company_branch.save(update_fields=["other_service_fees"])
    branch.other_service_fees = Decimal(overrides.get("station_fees", "5.00"))
    branch.save(update_fields=["other_service_fees"])
    set_balance(branch, overrides.get("branch_balance", "500.00"))
    set_balance(station, overrides.get("station_balance", "200.00"))
    car.balance = Decimal(overrides.get("car_balance", "1000.00"))
    car.is_blocked_balance_update = True
    car.save(update_fields=["balance", "is_blocked_balance_update"])


def complete_other(client, operation, service, cost="50"):
    return client.patch(
        other_url(operation.id),
        {
            "service": service.id,
            "cost": cost,
            "car_image": image_file("car.png"),
        },
        format="multipart",
    )


def test_patch_without_authentication_fail(api_client, other_operation, other_service):
    response = api_client.patch(
        other_url(other_operation.id),
        {"service": other_service.id, "cost": "50"},
        format="multipart",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    other_operation.refresh_from_db()
    assert other_operation.status == CarOperation.OperationStatus.PENDING
    assert other_operation.service_id is None


def test_get_not_allowed_fail(
    auth_client, station_worker, station, other_operation
):
    response = worker_client(auth_client, station_worker, station).get(
        other_url(other_operation.id)
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_patch_unknown_operation_fail(
    auth_client, station_worker, station, other_service, branch_other_service
):
    response = complete_other(
        worker_client(auth_client, station_worker, station),
        type("Op", (), {"id": 999_999})(),
        other_service,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_found"


def test_patch_wrong_worker_fail(
    auth_client,
    second_station_worker,
    station,
    other_operation,
    other_service,
    branch_other_service,
):
    response = complete_other(
        auth_client(second_station_worker, station_id=station.id),
        other_operation,
        other_service,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_found"
    other_operation.refresh_from_db()
    assert other_operation.status == CarOperation.OperationStatus.PENDING


def test_patch_gas_operation_with_service_fail(
    auth_client, station_worker, station, gas_operation, other_service, branch_other_service
):
    response = complete_other(
        worker_client(auth_client, station_worker, station),
        gas_operation,
        other_service,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_found"


@pytest.mark.parametrize(
    "op_status",
    [
        CarOperation.OperationStatus.COMPLETED,
        CarOperation.OperationStatus.CANCELLED,
    ],
)
def test_patch_finished_operation_fail(
    op_status,
    auth_client,
    station_worker,
    station,
    other_operation,
    other_service,
    branch_other_service,
):
    other_operation.status = op_status
    other_operation.save(update_fields=["status"])

    response = complete_other(
        worker_client(auth_client, station_worker, station),
        other_operation,
        other_service,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_found"


def test_patch_service_not_on_branch_fail(
    auth_client, station_worker, station, other_operation, other_service
):
    response = complete_other(
        worker_client(auth_client, station_worker, station),
        other_operation,
        other_service,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    other_operation.refresh_from_db()
    assert other_operation.status == CarOperation.OperationStatus.PENDING
    assert other_operation.service_id is None


def test_patch_without_car_image_fail(
    auth_client, station_worker, station, other_operation, other_service, branch_other_service
):
    response = worker_client(auth_client, station_worker, station).patch(
        other_url(other_operation.id),
        {"service": other_service.id, "cost": "50"},
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    other_operation.refresh_from_db()
    assert other_operation.status == CarOperation.OperationStatus.PENDING


def test_patch_cost_zero_fail(
    auth_client, station_worker, station, other_operation, other_service, branch_other_service
):
    response = complete_other(
        worker_client(auth_client, station_worker, station),
        other_operation,
        other_service,
        "0",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    other_operation.refresh_from_db()
    assert other_operation.status == CarOperation.OperationStatus.PENDING


def test_patch_insufficient_car_balance_fail(
    auth_client,
    station_worker,
    station,
    other_operation,
    other_service,
    branch_other_service,
    car,
    company_branch,
    branch,
    company,
):
    configure_other_money(
        company_branch, branch, car, station, car_balance="50.00"
    )
    # company cost = 50 * 1.10 = 55 > 50

    response = complete_other(
        worker_client(auth_client, station_worker, station),
        other_operation,
        other_service,
        "50",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_enough_balance"
    other_operation.refresh_from_db()
    car.refresh_from_db()
    branch.refresh_from_db()
    station.refresh_from_db()
    company.refresh_from_db()
    assert other_operation.status == CarOperation.OperationStatus.PENDING
    assert other_operation.service_id is None
    assert car.balance == Decimal("50.00")
    assert car.is_blocked_balance_update is True
    assert branch.balance == Decimal("500.00")
    assert station.balance == Decimal("200.00")
    assert CompanyKhaznaTransaction.objects.count() == 0
    assert StationKhaznaTransaction.objects.count() == 0
    assert Notification.objects.count() == 0


def test_complete_deducts_car_balance_and_notifies_right_users_success(
    auth_client,
    station_worker,
    station,
    other_operation,
    other_service,
    branch_other_service,
    car,
    company_branch,
    branch,
    company,
    company_owner,
    company_branch_manager,
    second_branch_company_manager,
    other_company_owner,
    station_owner,
    branch_manager,
    second_station_owner,
    other_station_owner,
    finance_user,
):
    configure_other_money(company_branch, branch, car, station)
    expected = other_costs("50", company_branch, branch)

    response = complete_other(
        worker_client(auth_client, station_worker, station),
        other_operation,
        other_service,
        "50",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["message"] == "تم اضافة الخدمه بنجاح"

    other_operation.refresh_from_db()
    car.refresh_from_db()
    branch.refresh_from_db()
    station.refresh_from_db()
    company.refresh_from_db()

    assert other_operation.status == CarOperation.OperationStatus.COMPLETED
    assert other_operation.service_id == other_service.id
    assert other_operation.cost == Decimal("50.00")
    assert other_operation.car_image
    assert car.balance == Decimal("1000.00") - expected["company_cost"]
    assert car.is_blocked_balance_update is False
    assert branch.balance == Decimal("500.00")
    assert station.balance == Decimal("200.00")
    assert company.balance == Decimal("0.00")

    station_txn = StationKhaznaTransaction.objects.get()
    assert station_txn.station_id == station.id
    assert station_txn.station_branch_id == branch.id
    assert station_txn.amount == expected["station_cost"]
    assert station_txn.is_internal is False
    assert station_txn.status == StationKhaznaTransaction.TransactionStatus.APPROVED

    company_txn = CompanyKhaznaTransaction.objects.get()
    assert company_txn.company_id == company.id
    assert company_txn.company_branch_id == company_branch.id
    assert company_txn.amount == expected["company_cost"]
    assert company_txn.is_internal is False
    assert other_service.name in company_txn.description

    station_money_users = notification_user_ids(
        Notification.NotificationType.MONEY, f"{expected['station_cost']:.2f}"
    )
    company_money_users = notification_user_ids(
        Notification.NotificationType.MONEY, f"{expected['company_cost']:.2f}"
    )

    assert station_money_users == {
        station_owner.id,
        branch_manager.id,
        second_station_owner.id,
        station_worker.id,
    }
    assert company_money_users == {
        company_owner.id,
        company_branch_manager.id,
        second_branch_company_manager.id,
        station_worker.id,
    }
    assert other_station_owner.id not in station_money_users
    assert other_company_owner.id not in company_money_users
    assert finance_user.id not in station_money_users | company_money_users
    assert (
        Notification.objects.filter(
            user_id=station_worker.id, type=Notification.NotificationType.MONEY
        ).count()
        == 2
    )
    company_note = Notification.objects.filter(
        user_id=company_owner.id, type=Notification.NotificationType.MONEY
    ).get()
    assert other_service.name in company_note.title
    assert "ABC 1234" in company_note.title


def test_complete_in_progress_other_operation_success(
    auth_client,
    station_worker,
    station,
    other_operation,
    other_service,
    branch_other_service,
    car,
    company_branch,
    branch,
):
    other_operation.status = CarOperation.OperationStatus.IN_PROGRESS
    other_operation.save(update_fields=["status"])
    configure_other_money(company_branch, branch, car, station)

    response = complete_other(
        worker_client(auth_client, station_worker, station),
        other_operation,
        other_service,
        "40",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    other_operation.refresh_from_db()
    assert other_operation.status == CarOperation.OperationStatus.COMPLETED
    assert other_operation.cost == Decimal("40.00")


def test_station_owner_cannot_complete_other_operation_fail(
    auth_client,
    station_owner,
    station,
    other_operation,
    other_service,
    branch_other_service,
):
    response = complete_other(
        auth_client(station_owner, station_id=station.id),
        other_operation,
        other_service,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_found"
