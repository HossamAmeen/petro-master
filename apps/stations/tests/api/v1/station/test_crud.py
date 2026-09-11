import pytest
from django.urls import reverse
from rest_framework import status

from apps.stations.models.stations_models import Station
from apps.stations.tests.helpers import (
    returned_ids,
    stations_detail_url,
    stations_list_url,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationCRUD:
    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(stations_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        ["company_owner", "station_owner", "station_worker", "branch_manager"],
    )
    def test_list_forbidden_role_fail(
        self, role_fixture, request, auth_client, company, station
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker", "branch_manager"}:
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).get(stations_list_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize("role_fixture", ["admin_user", "finance_user"])
    def test_list_dashboard_success(
        self, role_fixture, request, auth_client, station, other_station
    ):
        user = request.getfixturevalue(role_fixture)

        response = auth_client(user).get(stations_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        assert {station.id, other_station.id}.issubset(returned_ids(response))

    def test_list_includes_annotated_counts_success(
        self,
        auth_client,
        admin_user,
        station,
        branch,
        station_owner,
        branch_manager,
        station_worker,
        branch_petrol_service,
        other_station,
    ):
        response = auth_client(admin_user).get(stations_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[station.id]
        assert row["name"] == station.name
        assert row["branches_count"] >= 1
        assert row["workers_count"] >= 1
        assert "total_balance" in row
        assert "district" in row
        assert listed[other_station.id]["name"] == other_station.name

    def test_list_search_by_name_success(
        self, auth_client, admin_user, station, other_station
    ):
        station.name = "UniqueAlphaStation"
        station.save(update_fields=["name"])

        response = auth_client(admin_user).get(
            stations_list_url(search="UniqueAlphaStation", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station.id in ids
        assert other_station.id not in ids

    def test_list_filter_by_district_success(
        self, auth_client, admin_user, station, geo_data, station_factory
    ):
        from apps.geo.models import City, District

        city = City.objects.create(name="Giza", country=geo_data["country"])
        district = District.objects.create(name="Dokki", city=city)
        other = station_factory(name="Giza Station", district=district)

        response = auth_client(admin_user).get(
            stations_list_url(district=geo_data["district"].id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station.id in ids
        assert other.id not in ids

    def test_retrieve_without_authentication_fail(self, api_client, station):
        response = api_client.get(stations_detail_url(station.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_as_dashboard_success(
        self, auth_client, admin_user, station, branch
    ):
        response = auth_client(admin_user).get(stations_detail_url(station.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == station.id
        assert response.data["name"] == station.name
        assert response.data["address"] == station.address
        assert response.data["branches_count"] >= 1

    def test_retrieve_as_station_owner_success(
        self, auth_client, station_owner, station
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            stations_detail_url(station.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == station.id

    def test_retrieve_forbidden_company_role_fail(
        self, auth_client, company_owner, company, station
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            stations_detail_url(station.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_without_authentication_fail(
        self, api_client, station_payload_factory
    ):
        response = api_client.post(
            reverse("stations-list"),
            station_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Station.objects.filter(name="New Station 1").count() == 0

    @pytest.mark.parametrize(
        "role_fixture",
        ["station_owner", "station_worker", "company_owner"],
    )
    def test_create_forbidden_role_fail(
        self,
        role_fixture,
        request,
        auth_client,
        company,
        station,
        station_payload_factory,
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker"}:
            client_kwargs["station_id"] = station.id
        existing = set(Station.objects.values_list("id", flat=True))

        response = auth_client(user, **client_kwargs).post(
            reverse("stations-list"),
            station_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert set(Station.objects.values_list("id", flat=True)) == existing

    def test_create_as_admin_success(
        self, auth_client, admin_user, geo_data, station_payload_factory
    ):
        payload = station_payload_factory()

        response = auth_client(admin_user).post(
            reverse("stations-list"), payload, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = Station.objects.get(name=payload["name"])
        assert created.address == payload["address"]
        assert created.district_id == geo_data["district"].id
        assert created.balance == 0
        assert created.created_by_id == admin_user.id

    def test_update_as_admin_success(self, auth_client, admin_user, station):
        response = auth_client(admin_user).patch(
            stations_detail_url(station.id),
            {"name": "Renamed Station", "balance": "999.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        station.refresh_from_db()
        assert station.name == "Renamed Station"
        assert station.balance == 0

    def test_update_as_station_owner_success(self, auth_client, station_owner, station):
        response = auth_client(station_owner, station_id=station.id).patch(
            stations_detail_url(station.id),
            {"address": "New Address Line"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        station.refresh_from_db()
        assert station.address == "New Address Line"

    def test_delete_empty_station_as_admin_success(
        self, auth_client, admin_user, station_factory
    ):
        empty = station_factory(name="Deletable Station")

        response = auth_client(admin_user).delete(stations_detail_url(empty.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Station.objects.filter(id=empty.id).exists()

    @pytest.mark.parametrize("role_fixture", ["station_worker", "branch_manager"])
    def test_retrieve_as_station_role_success(
        self, role_fixture, request, auth_client, station
    ):
        user = request.getfixturevalue(role_fixture)

        response = auth_client(user, station_id=station.id).get(
            stations_detail_url(station.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == station.id

    def test_retrieve_unknown_station_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(stations_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_missing_name_fail(
        self, auth_client, admin_user, station_payload_factory
    ):
        payload = station_payload_factory()
        payload.pop("name")

        response = auth_client(admin_user).post(
            reverse("stations-list"), payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
    def test_create_as_dashboard_role_success(
        self, role_fixture, request, auth_client, station_payload_factory
    ):
        user = request.getfixturevalue(role_fixture)
        payload = station_payload_factory()

        response = auth_client(user).post(
            reverse("stations-list"), payload, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Station.objects.filter(name=payload["name"]).exists()

    def test_update_forbidden_company_role_fail(
        self, auth_client, company_owner, company, station
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            stations_detail_url(station.id),
            {"name": "Hacked"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        station.refresh_from_db()
        assert station.name == "Station 1"

    @pytest.mark.parametrize("role_fixture", ["station_worker", "branch_manager"])
    def test_update_as_station_role_success(
        self, role_fixture, request, auth_client, station
    ):
        user = request.getfixturevalue(role_fixture)

        response = auth_client(user, station_id=station.id).patch(
            stations_detail_url(station.id),
            {"address": f"Updated by {role_fixture}"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        station.refresh_from_db()
        assert station.address == f"Updated by {role_fixture}"

    def test_list_filter_by_name_success(
        self, auth_client, admin_user, station, other_station
    ):
        response = auth_client(admin_user).get(
            stations_list_url(name=station.name, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station.id in ids
        assert other_station.id not in ids

    def test_list_search_by_address_success(
        self, auth_client, admin_user, station, other_station
    ):
        station.address = "UniqueStationStreet"
        station.save(update_fields=["address"])

        response = auth_client(admin_user).get(
            stations_list_url(search="UniqueStationStreet", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station.id in ids
        assert other_station.id not in ids
