import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import operation_detail_url
from apps.stations.tests.helpers import (
    operations_url,
    other_url,
    returned_ids,
    worker_client,
)
from apps.utilities.testing import assert_soft_deleted

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationOtherOperationDelete:
    def test_delete_without_authentication_fail(self, api_client, other_operation):
        response = api_client.delete(other_url(other_operation.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CarOperation.objects.filter(id=other_operation.id).exists()

    def test_delete_pending_unblocks_car_success(
        self, auth_client, station_worker, station, other_operation, car
    ):
        car.is_blocked_balance_update = True
        car.save(update_fields=["is_blocked_balance_update"])

        response = worker_client(auth_client, station_worker, station).delete(
            other_url(other_operation.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CarOperation.objects.filter(id=other_operation.id).exists()
        car.refresh_from_db()
        assert car.is_blocked_balance_update is False

    def test_delete_wrong_worker_fail(
        self, auth_client, second_station_worker, station, other_operation
    ):
        response = auth_client(second_station_worker, station_id=station.id).delete(
            other_url(other_operation.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        assert CarOperation.objects.filter(id=other_operation.id).exists()

    def test_delete_gas_operation_fail(
        self, auth_client, station_worker, station, gas_operation
    ):
        response = worker_client(auth_client, station_worker, station).delete(
            other_url(gas_operation.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        assert CarOperation.objects.filter(id=gas_operation.id).exists()

    @pytest.mark.parametrize(
        "op_status",
        [
            CarOperation.OperationStatus.COMPLETED,
            CarOperation.OperationStatus.CANCELLED,
        ],
    )
    def test_delete_finished_operation_fail(
        self, op_status, auth_client, station_worker, station, other_operation
    ):
        other_operation.status = op_status
        other_operation.save(update_fields=["status"])

        response = worker_client(auth_client, station_worker, station).delete(
            other_url(other_operation.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        assert CarOperation.objects.filter(id=other_operation.id).exists()

    def test_delete_unknown_operation_fail(self, auth_client, station_worker, station):
        response = worker_client(auth_client, station_worker, station).delete(
            other_url(999_999)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"

    def test_delete_in_progress_unblocks_car_success(
        self, auth_client, station_worker, station, other_operation, car
    ):
        other_operation.status = CarOperation.OperationStatus.IN_PROGRESS
        other_operation.save(update_fields=["status"])
        car.is_blocked_balance_update = True
        car.save(update_fields=["is_blocked_balance_update"])

        response = worker_client(auth_client, station_worker, station).delete(
            other_url(other_operation.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CarOperation.objects.filter(id=other_operation.id).exists()
        car.refresh_from_db()
        assert car.is_blocked_balance_update is False


class TestStationOtherOperationSoftDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, station_worker, station, other_operation):
        self.client = worker_client(auth_client, station_worker, station)
        self.operation = other_operation
        response = self.client.delete(other_url(other_operation.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(CarOperation, self.operation.id)

    def test_deleted_operation_hidden_from_station_list_success(self):
        response = self.client.get(operations_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        assert self.operation.id not in returned_ids(response)

    def test_retrieve_deleted_operation_not_found_fail(self):
        response = self.client.get(operation_detail_url(self.operation.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_operation_fail(self):
        """Like an unknown id, the view answers 400 `not_found`."""
        response = self.client.delete(other_url(self.operation.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
