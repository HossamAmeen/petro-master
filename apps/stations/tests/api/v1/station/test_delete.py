import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.stations.models.stations_models import Station, StationBranch
from apps.stations.tests.helpers import stations_detail_url, stations_list_url
from apps.utilities.testing import assert_soft_deleted, listed_ids

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


class TestStationSoftDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, station_factory):
        self.client = auth_client(admin_user)
        self.station = station_factory()
        response = self.client.delete(stations_detail_url(self.station.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(Station, self.station.id)

    def test_deleted_station_hidden_from_list_success(self, station):
        response = self.client.get(stations_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = listed_ids(response)
        assert self.station.id not in ids
        assert station.id in ids

    def test_retrieve_deleted_station_not_found_fail(self):
        response = self.client.get(stations_detail_url(self.station.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_station_not_found_fail(self):
        response = self.client.delete(stations_detail_url(self.station.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_station_with_branch_keeps_branch_active_success(
        self, station_factory, station_branch_factory
    ):
        """Soft delete skips `on_delete=PROTECT`: branches stay active."""
        station = station_factory()
        branch = station_branch_factory(station=station)

        response = self.client.delete(stations_detail_url(station.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert_soft_deleted(Station, station.id)
        assert StationBranch.objects.filter(id=branch.id).exists()
