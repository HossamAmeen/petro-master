import pytest
from django.urls import reverse


@pytest.mark.django_db
class TestStationViews:
    def test_station_list_dashboard_permission(self, auth_client, admin_user, station):
        client = auth_client(admin_user)
        url = reverse("stations-list")
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1
        assert response.data["results"][0]["name"] == station.name

    @pytest.mark.parametrize(
        ("is_available", "query_params", "should_be_returned"),
        [
            (True, {}, True),
            (False, {}, False),
            (True, {"is_available": "true"}, True),
            (False, {"is_available": "false"}, True),
        ],
    )
    def test_station_list_filters_availability(
        self,
        auth_client,
        admin_user,
        station,
        is_available,
        query_params,
        should_be_returned,
    ):
        station.is_available = is_available
        station.save(update_fields=["is_available"])

        response = auth_client(admin_user).get(
            reverse("stations-list"), data=query_params
        )

        assert response.status_code == 200
        station_ids = {result["id"] for result in response.data["results"]}
        assert (station.id in station_ids) is should_be_returned

    @pytest.mark.parametrize("role_fixture, expected_keys", [
        ("station_owner", ["station_name", "balance", "workers_count"]),
        ("branch_manager", ["station_name", "branches_count"]),
        ("station_worker", ["balance", "workers_count"]),
    ])
    def test_station_home_roles(self, request, auth_client, station, branch, role_fixture, expected_keys):
        # We use request.getfixturevalue to dynamically load the user fixture based on parameterization
        user = request.getfixturevalue(role_fixture)
        client = auth_client(user, station_id=station.id)
        
        url = reverse("station-home")
        response = client.get(url)
        
        assert response.status_code == 200
        for key in expected_keys:
            assert key in response.data
            
        if role_fixture == "station_worker":
            assert response.data["balance"] == 0
            assert response.data["workers_count"] == 0

    def test_station_operations_list(self, auth_client, station_worker, station, gas_operation):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-operations")
        response = client.get(url)
        assert response.status_code == 200
        assert "results" in response.data
        assert "current_balance" in response.data
        
    def test_station_reports_list(self, auth_client, station_worker, station, gas_operation):
        client = auth_client(station_worker, station_id=station.id)
        url = reverse("station-reports")
        response = client.get(url)
        assert response.status_code == 200
        assert "operations" in response.data
        assert "cash_request_balance" in response.data
