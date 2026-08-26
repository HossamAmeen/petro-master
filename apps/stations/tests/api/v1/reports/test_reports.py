from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.operation_model import CarOperation
from apps.stations.tests.helpers import reports_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_reports_without_authentication_fail(api_client):
    response = api_client.get(reports_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "role_fixture",
    ["admin_user", "company_owner"],
)
def test_reports_forbidden_role_fail(
    role_fixture, request, auth_client, company, station
):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture == "company_owner":
        client_kwargs["company_id"] = company.id

    response = auth_client(user, **client_kwargs).get(reports_url())

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_reports_owner_aggregates_operations_and_cash_success(
    auth_client,
    station_owner,
    station,
    branch,
    gas_operation,
    other_service,
    car_operation_factory,
    cash_request_factory,
    company,
    driver,
    station_worker,
):
    gas_operation.status = CarOperation.OperationStatus.COMPLETED
    gas_operation.station_cost = Decimal("100.00")
    gas_operation.amount = Decimal("10.00")
    gas_operation.save(update_fields=["status", "station_cost", "amount"])
    wash = car_operation_factory(
        service=other_service,
        station_cost=Decimal("40.00"),
        amount=Decimal("1.00"),
        status=CarOperation.OperationStatus.COMPLETED,
    )
    cash_request_factory(
        company=company,
        driver=driver,
        station=station,
        station_branch=branch,
        status=CompanyCashRequest.Status.APPROVED,
        amount=Decimal("75.00"),
        approved_by=station_worker,
    )
    cash_request_factory(
        company=company,
        driver=driver,
        station=station,
        station_branch=branch,
        status=CompanyCashRequest.Status.IN_PROGRESS,
        amount=Decimal("20.00"),
        approved_by=station_worker,
    )

    response = auth_client(station_owner, station_id=station.id).get(reports_url())

    assert response.status_code == status.HTTP_200_OK
    assert response.data["station_id"] == station.id
    assert Decimal(str(response.data["cash_request_balance"])) == Decimal("75.00")
    by_service = {row["service"]: row for row in response.data["operations"]}
    assert by_service[gas_operation.service_id]["count"] == 1
    assert Decimal(str(by_service[gas_operation.service_id]["total_balance"])) == Decimal(
        "100.00"
    )
    assert Decimal(str(by_service[gas_operation.service_id]["amount"])) == Decimal(
        "10.00"
    )
    assert by_service[gas_operation.service_id]["service_name"] == gas_operation.service.name
    assert by_service[other_service.id]["count"] == 1
    assert Decimal(str(by_service[other_service.id]["total_balance"])) == Decimal("40.00")
    assert wash.id  # created for aggregation


def test_reports_worker_sees_own_ops_and_approved_cash_success(
    auth_client,
    station_worker,
    second_station_worker,
    station,
    branch,
    gas_operation,
    car_operation_factory,
    cash_request_factory,
    company,
    driver,
):
    gas_operation.station_cost = Decimal("80.00")
    gas_operation.save(update_fields=["station_cost"])
    car_operation_factory(
        worker=second_station_worker,
        station_cost=Decimal("50.00"),
    )
    cash_request_factory(
        company=company,
        driver=driver,
        station=station,
        station_branch=branch,
        status=CompanyCashRequest.Status.APPROVED,
        amount=Decimal("30.00"),
        approved_by=station_worker,
    )
    cash_request_factory(
        company=company,
        driver=driver,
        station=station,
        station_branch=branch,
        status=CompanyCashRequest.Status.APPROVED,
        amount=Decimal("90.00"),
        approved_by=second_station_worker,
    )

    response = auth_client(station_worker, station_id=station.id).get(reports_url())

    assert response.status_code == status.HTTP_200_OK
    assert Decimal(str(response.data["cash_request_balance"])) == Decimal("30.00")
    totals = {
        row["service"]: Decimal(str(row["total_balance"]))
        for row in response.data["operations"]
    }
    assert totals[gas_operation.service_id] == Decimal("80.00")


def test_reports_branch_manager_excludes_other_branch_success(
    auth_client,
    branch_manager,
    station,
    gas_operation,
    second_station_branch,
    car_operation_factory,
):
    gas_operation.station_cost = Decimal("25.00")
    gas_operation.save(update_fields=["station_cost"])
    car_operation_factory(
        station_branch=second_station_branch,
        station_cost=Decimal("70.00"),
    )

    response = auth_client(branch_manager, station_id=station.id).get(reports_url())

    assert response.status_code == status.HTTP_200_OK
    totals = {
        row["service"]: Decimal(str(row["total_balance"]))
        for row in response.data["operations"]
    }
    assert totals[gas_operation.service_id] == Decimal("25.00")


def test_reports_date_from_excludes_older_ops_success(
    auth_client, station_owner, station, gas_operation, car_operation_factory
):
    old = car_operation_factory(station_cost=Decimal("15.00"))
    CarOperation.objects.filter(id=old.id).update(
        modified=timezone.localtime() - timedelta(days=5)
    )
    gas_operation.station_cost = Decimal("10.00")
    gas_operation.save(update_fields=["station_cost"])
    today = timezone.localdate().isoformat()

    response = auth_client(station_owner, station_id=station.id).get(
        reports_url(date_from=today)
    )

    assert response.status_code == status.HTTP_200_OK
    totals = {
        row["service"]: Decimal(str(row["total_balance"]))
        for row in response.data["operations"]
    }
    assert totals.get(gas_operation.service_id) == Decimal("10.00")


def test_reports_date_to_excludes_newer_ops_success(
    auth_client, station_owner, station, gas_operation, car_operation_factory
):
    older = car_operation_factory(station_cost=Decimal("40.00"))
    CarOperation.objects.filter(id=older.id).update(
        modified=timezone.localtime() - timedelta(days=3)
    )
    gas_operation.station_cost = Decimal("10.00")
    gas_operation.save(update_fields=["station_cost"])
    cutoff = (timezone.localdate() - timedelta(days=1)).isoformat()

    response = auth_client(station_owner, station_id=station.id).get(
        reports_url(date_from=(timezone.localdate() - timedelta(days=10)).isoformat(), date_to=cutoff)
    )

    assert response.status_code == status.HTTP_200_OK
    balances = {
        Decimal(str(row["total_balance"])) for row in response.data["operations"]
    }
    assert Decimal("40.00") in balances
    assert Decimal("10.00") not in balances


def test_reports_empty_when_no_ops_success(auth_client, station_owner, station):
    response = auth_client(station_owner, station_id=station.id).get(reports_url())

    assert response.status_code == status.HTTP_200_OK
    assert response.data["station_id"] == station.id
    assert Decimal(str(response.data["cash_request_balance"])) == Decimal("0")
    assert response.data["operations"] == []


def test_reports_time_window_success(
    auth_client, station_owner, station, gas_operation
):
    gas_operation.station_cost = Decimal("12.00")
    gas_operation.save(update_fields=["station_cost"])

    inside = auth_client(station_owner, station_id=station.id).get(
        reports_url(time_from="00:00:00", time_to="23:59:59")
    )
    outside = auth_client(station_owner, station_id=station.id).get(
        reports_url(time_from="00:00:00", time_to="00:00:01")
    )

    assert inside.status_code == status.HTTP_200_OK
    assert outside.status_code == status.HTTP_200_OK
    inside_totals = {
        row["service"]: Decimal(str(row["total_balance"]))
        for row in inside.data["operations"]
    }
    assert inside_totals.get(gas_operation.service_id) == Decimal("12.00")


def test_reports_forbidden_finance_fail(auth_client, finance_user, station):
    response = auth_client(finance_user, station_id=station.id).get(reports_url())

    assert response.status_code == status.HTTP_403_FORBIDDEN
