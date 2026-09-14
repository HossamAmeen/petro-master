import pytest
from rest_framework import status

from apps.stations.tests.helpers import returned_ids, stations_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationList:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, station):
        self.auth_client = auth_client
        self.station = station
        self.url = stations_list_url()

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        ["company_owner", "station_owner", "station_worker", "branch_manager"],
    )
    def test_list_forbidden_role_fail(self, role_fixture, request, company):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker", "branch_manager"}:
            client_kwargs["station_id"] = self.station.id

        response = self.auth_client(user, **client_kwargs).get(self.url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("role_fixture", ["admin_user", "finance_user"])
    def test_list_dashboard_success(self, role_fixture, request, other_station):
        user = request.getfixturevalue(role_fixture)

        response = self.auth_client(user).get(self.url, {"no_paginate": "true"})

        assert response.status_code == status.HTTP_200_OK
        assert {self.station.id, other_station.id}.issubset(returned_ids(response))

    def test_list_includes_annotated_counts_success(
        self,
        admin_user,
        branch,
        station_owner,
        branch_manager,
        station_worker,
        branch_petrol_service,
        other_station,
    ):
        response = self.auth_client(admin_user).get(self.url, {"no_paginate": "true"})

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[self.station.id]
        assert row["name"] == self.station.name
        assert row["branches_count"] >= 1
        assert row["workers_count"] >= 1
        assert "total_balance" in row
        assert "district" in row
        assert listed[other_station.id]["name"] == other_station.name

    def test_list_search_by_name_success(self, admin_user, other_station):
        self.station.name = "UniqueAlphaStation"
        self.station.save(update_fields=["name"])

        response = self.auth_client(admin_user).get(
            self.url, {"search": "UniqueAlphaStation", "no_paginate": "true"}
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert self.station.id in ids
        assert other_station.id not in ids

    def test_list_search_by_address_success(self, admin_user, other_station):
        self.station.address = "UniqueStationStreet"
        self.station.save(update_fields=["address"])

        response = self.auth_client(admin_user).get(
            self.url, {"search": "UniqueStationStreet", "no_paginate": "true"}
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert self.station.id in ids
        assert other_station.id not in ids

    def test_list_filter_by_name_success(self, admin_user, other_station):
        response = self.auth_client(admin_user).get(
            self.url, {"name": self.station.name, "no_paginate": "true"}
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert self.station.id in ids
        assert other_station.id not in ids

    def test_list_filter_by_district_success(
        self, admin_user, geo_data, station_factory
    ):
        from apps.geo.models import City, District

        city = City.objects.create(name="Giza", country=geo_data["country"])
        district = District.objects.create(name="Dokki", city=city)
        other = station_factory(name="Giza Station", district=district)

        response = self.auth_client(admin_user).get(
            self.url, {"district": geo_data["district"].id, "no_paginate": "true"}
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert self.station.id in ids
        assert other.id not in ids
