from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.stations.tests.helpers import operations_url, returned_ids, set_balance

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationOperations:
    def test_operations_without_authentication_fail(self, api_client):
        response = api_client.get(operations_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_operations_worker_sees_own_only_success(
        self,
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
        self,
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
        self,
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
        self,
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
        self, auth_client, station_owner, station, gas_operation, car_operation_factory
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
        self,
        auth_client,
        station_owner,
        station,
        gas_operation,
        driver,
        car_operation_factory,
    ):
        other = car_operation_factory()

        response = auth_client(station_owner, station_id=station.id).get(
            operations_url(search=driver.name, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert gas_operation.id in ids
        assert other.id not in ids

    def test_operations_diesel_counts_as_petrol_balance_success(
        self,
        auth_client,
        station_owner,
        station,
        diesel_service,
        car_operation_factory,
    ):
        diesel_op = car_operation_factory(
            service=diesel_service,
            station_cost=Decimal("33.00"),
            status=CarOperation.OperationStatus.COMPLETED,
        )

        response = auth_client(station_owner, station_id=station.id).get(
            operations_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert diesel_op.id in returned_ids(response)
        assert Decimal(str(response.data["petrol_balance"])) == Decimal("33.00")
        assert Decimal(str(response.data["other_balance"])) == Decimal("0")

    def test_operations_empty_balances_success(
        self, auth_client, station_owner, station
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            operations_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []
        assert Decimal(str(response.data["petrol_balance"])) == Decimal("0")
        assert Decimal(str(response.data["other_balance"])) == Decimal("0")
        assert Decimal(str(response.data["total_balance"])) == Decimal("0")

    def test_operations_filter_by_worker_and_service_success(
        self,
        auth_client,
        station_owner,
        station,
        gas_operation,
        service,
        other_service,
        second_station_worker,
        car_operation_factory,
    ):
        other = car_operation_factory(
            worker=second_station_worker, service=other_service
        )

        by_worker = auth_client(station_owner, station_id=station.id).get(
            operations_url(worker=gas_operation.worker_id, no_paginate="true")
        )
        by_service = auth_client(station_owner, station_id=station.id).get(
            operations_url(service=service.id, no_paginate="true")
        )

        assert by_worker.status_code == status.HTTP_200_OK
        assert by_service.status_code == status.HTTP_200_OK
        assert gas_operation.id in returned_ids(by_worker)
        assert other.id not in returned_ids(by_worker)
        assert gas_operation.id in returned_ids(by_service)
        assert other.id not in returned_ids(by_service)

    def test_operations_search_by_code_success(
        self, auth_client, station_owner, station, gas_operation, car_operation_factory
    ):
        gas_operation.code = "GASCODE99"
        gas_operation.save(update_fields=["code"])
        other = car_operation_factory(code="OTHERCODE")

        response = auth_client(station_owner, station_id=station.id).get(
            operations_url(search="GASCODE99", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert gas_operation.id in ids
        assert other.id not in ids

    def test_operations_status_comma_filter_success(
        self, auth_client, station_owner, station, gas_operation, car_operation_factory
    ):
        done = car_operation_factory(status=CarOperation.OperationStatus.COMPLETED)
        cancelled = car_operation_factory(status=CarOperation.OperationStatus.CANCELLED)

        response = auth_client(station_owner, station_id=station.id).get(
            operations_url(status="pending,completed", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert gas_operation.id in ids
        assert done.id in ids
        assert cancelled.id not in ids
