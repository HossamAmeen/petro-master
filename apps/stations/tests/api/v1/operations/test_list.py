from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.stations.tests.helpers import operations_url, returned_ids, set_balance


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_operations_without_authentication_fail(api_client):
    response = api_client.get(operations_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_operations_worker_sees_own_only_success(
    auth_client,
    station_worker,
    second_station_worker,
    station,
    gas_operation,
    car_operation_factory,
):
    other = car_operation_factory(worker=second_station_worker)

    response = auth_client(station_worker, station_id=station.id).get(
        operations_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert gas_operation.id in ids
    assert other.id not in ids
    assert "current_balance" in response.data
    assert "petrol_balance" in response.data
    assert "other_balance" in response.data
    assert "total_balance" in response.data


def test_operations_owner_sees_station_ops_not_other_station_success(
    auth_client,
    station_owner,
    station,
    gas_operation,
    other_station_branch,
    car_operation_factory,
):
    foreign = car_operation_factory(station_branch=other_station_branch)

    response = auth_client(station_owner, station_id=station.id).get(
        operations_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert gas_operation.id in ids
    assert foreign.id not in ids


def test_operations_branch_manager_scoped_success(
    auth_client,
    branch_manager,
    station,
    gas_operation,
    second_station_branch,
    car_operation_factory,
):
    other = car_operation_factory(station_branch=second_station_branch)

    response = auth_client(branch_manager, station_id=station.id).get(
        operations_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert gas_operation.id in ids
    assert other.id not in ids


def test_operations_balances_split_by_service_type_success(
    auth_client,
    station_owner,
    station,
    gas_operation,
    other_service,
    car_operation_factory,
):
    set_balance(station, "75.00")
    gas_operation.status = CarOperation.OperationStatus.COMPLETED
    gas_operation.station_cost = Decimal("100.00")
    gas_operation.save(update_fields=["status", "station_cost"])
    wash = car_operation_factory(
        service=other_service,
        station_cost=Decimal("40.00"),
        status=CarOperation.OperationStatus.COMPLETED,
    )

    response = auth_client(station_owner, station_id=station.id).get(
        operations_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    assert Decimal(str(response.data["current_balance"])) == Decimal("75.00")
    assert Decimal(str(response.data["petrol_balance"])) == Decimal("100.00")
    assert Decimal(str(response.data["other_balance"])) == Decimal("40.00")
    assert Decimal(str(response.data["total_balance"])) == Decimal("140.00")
    assert {gas_operation.id, wash.id}.issubset(returned_ids(response))
    row = next(
        item for item in response.data["results"] if item["id"] == gas_operation.id
    )
    assert row["service"]["id"] == gas_operation.service_id
    assert row["company_name"]
    assert row["service_category"] == "خدمات بترولية"


def test_operations_filter_by_status_success(
    auth_client, station_owner, station, gas_operation, car_operation_factory
):
    done = car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)

    response = auth_client(station_owner, station_id=station.id).get(
        operations_url(status="completed", no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert done.id in ids
    assert gas_operation.id not in ids


def test_operations_search_by_driver_name_success(
    auth_client, station_owner, station, gas_operation, driver, car_operation_factory
):
    other = car_operation_factory()

    response = auth_client(station_owner, station_id=station.id).get(
        operations_url(search=driver.name, no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert gas_operation.id in ids
    assert other.id not in ids
