import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.stations.tests.helpers import gas_url, worker_client


pytestmark = [pytest.mark.api, pytest.mark.django_db]



class TestStationGasOperationDelete:
    def test_delete_without_authentication_fail(self, api_client, gas_operation):
        response = api_client.delete(gas_url(gas_operation.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CarOperation.objects.filter(id=gas_operation.id).exists()


    def test_delete_pending_unblocks_car_success(self,
        auth_client, station_worker, station, gas_operation, car
    ):
        car.is_blocked_balance_update = True
        car.save(update_fields=["is_blocked_balance_update"])

        response = worker_client(auth_client, station_worker, station).delete(
            gas_url(gas_operation.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CarOperation.objects.filter(id=gas_operation.id).exists()
        car.refresh_from_db()
        assert car.is_blocked_balance_update is False


    def test_delete_in_progress_success(self,
        auth_client, station_worker, station, gas_operation, car
    ):
        gas_operation.status = CarOperation.OperationStatus.IN_PROGRESS
        gas_operation.save(update_fields=["status"])
        car.is_blocked_balance_update = True
        car.save(update_fields=["is_blocked_balance_update"])

        response = worker_client(auth_client, station_worker, station).delete(
            gas_url(gas_operation.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CarOperation.objects.filter(id=gas_operation.id).exists()
        car.refresh_from_db()
        assert car.is_blocked_balance_update is False


    @pytest.mark.parametrize(
        "op_status",
        [
            CarOperation.OperationStatus.COMPLETED,
            CarOperation.OperationStatus.CANCELLED,
        ],
    )
    def test_delete_finished_operation_fail(self,
        op_status, auth_client, station_worker, station, gas_operation
    ):
        gas_operation.status = op_status
        gas_operation.save(update_fields=["status"])

        response = worker_client(auth_client, station_worker, station).delete(
            gas_url(gas_operation.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        assert CarOperation.objects.filter(id=gas_operation.id).exists()


    def test_delete_unknown_operation_fail(self, auth_client, station_worker, station):
        response = worker_client(auth_client, station_worker, station).delete(
            gas_url(999_999)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"


    def test_delete_by_another_authenticated_user_success(self,
        auth_client, second_station_worker, station, gas_operation
    ):
        response = auth_client(second_station_worker, station_id=station.id).delete(
            gas_url(gas_operation.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CarOperation.objects.filter(id=gas_operation.id).exists()
