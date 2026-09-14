import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.stations.models.stations_models import Station
from apps.stations.tests.helpers import stations_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, station):
        self.client = auth_client(admin_user)
        self.station = station
        self.url = stations_detail_url(station.id)

    def test_delete_without_authentication_fail(self, api_client):
        response = api_client.delete(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Station.objects.filter(id=self.station.id).exists()

    def test_delete_empty_station_as_admin_success(self):
        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Station.objects.filter(id=self.station.id).exists()

    @pytest.mark.parametrize("operation_status", CarOperation.OperationStatus.values)
    def test_delete_station_with_operations_fail(
        self, operation_status, car_operation_factory
    ):
        operation = car_operation_factory(status=operation_status)

        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "has_operations"
        assert Station.objects.filter(id=self.station.id).exists()
        assert CarOperation.objects.filter(id=operation.id).exists()

    def test_delete_station_without_own_operations_success(
        self, car_operation_factory, station_factory
    ):
        car_operation_factory()
        target = station_factory()

        response = self.client.delete(stations_detail_url(target.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Station.objects.filter(id=target.id).exists()

    def test_delete_unknown_station_fail(self):
        response = self.client.delete(stations_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
