import pytest
from rest_framework import status

from apps.stations.tests.helpers import stations_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationUpdate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, station):
        self.auth_client = auth_client
        self.station = station
        self.url = stations_detail_url(station.id)

    def test_update_as_admin_success(self, admin_user):
        response = self.auth_client(admin_user).patch(
            self.url,
            {"name": "Renamed Station", "balance": "999.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.station.refresh_from_db()
        assert self.station.name == "Renamed Station"
        assert self.station.balance == 0

    def test_update_as_station_owner_success(self, station_owner):
        response = self.auth_client(station_owner, station_id=self.station.id).patch(
            self.url,
            {"address": "New Address Line"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.station.refresh_from_db()
        assert self.station.address == "New Address Line"

    @pytest.mark.parametrize("role_fixture", ["station_worker", "branch_manager"])
    def test_update_as_station_role_success(self, role_fixture, request):
        user = request.getfixturevalue(role_fixture)

        response = self.auth_client(user, station_id=self.station.id).patch(
            self.url,
            {"address": f"Updated by {role_fixture}"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        self.station.refresh_from_db()
        assert self.station.address == f"Updated by {role_fixture}"

    def test_update_forbidden_company_role_fail(self, company_owner, company):
        response = self.auth_client(company_owner, company_id=company.id).patch(
            self.url,
            {"name": "Hacked"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        self.station.refresh_from_db()
        assert self.station.name == "Station 1"
