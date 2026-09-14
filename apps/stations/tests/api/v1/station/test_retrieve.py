import pytest
from rest_framework import status

from apps.stations.tests.helpers import stations_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationRetrieve:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, station):
        self.auth_client = auth_client
        self.station = station
        self.url = stations_detail_url(station.id)

    def test_retrieve_without_authentication_fail(self, api_client):
        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_as_dashboard_success(self, admin_user, branch):
        response = self.auth_client(admin_user).get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.station.id
        assert response.data["name"] == self.station.name
        assert response.data["address"] == self.station.address
        assert response.data["branches_count"] >= 1

    def test_retrieve_as_station_owner_success(self, station_owner):
        response = self.auth_client(station_owner, station_id=self.station.id).get(
            self.url
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.station.id

    @pytest.mark.parametrize("role_fixture", ["station_worker", "branch_manager"])
    def test_retrieve_as_station_role_success(self, role_fixture, request):
        user = request.getfixturevalue(role_fixture)

        response = self.auth_client(user, station_id=self.station.id).get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.station.id

    def test_retrieve_forbidden_company_role_fail(self, company_owner, company):
        response = self.auth_client(company_owner, company_id=company.id).get(
            self.url
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_unknown_station_fail(self, admin_user):
        response = self.auth_client(admin_user).get(stations_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
