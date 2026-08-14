import pytest
from django.urls import reverse


@pytest.mark.api
@pytest.mark.django_db
class TestStationAPI:
    def test_list_requires_dashboard_authentication(self, api_client):
        response = api_client.get(reverse("stations-list"))

        assert response.status_code == 401

    def test_admin_lists_stations(self, auth_client, admin_user, station):
        client = auth_client(admin_user)

        response = client.get(reverse("stations-list"))

        assert response.status_code == 200
        station_ids = {item["id"] for item in response.data["results"]}
        assert station.id in station_ids
