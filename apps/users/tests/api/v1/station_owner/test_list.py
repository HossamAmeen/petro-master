import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import returned_ids, station_owners_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_list_without_authentication_fail(api_client):
    response = api_client.get(station_owners_list_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_as_company_owner_fail(auth_client, company_owner, company):
    response = auth_client(company_owner, company_id=company.id).get(
        station_owners_list_url()
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_as_driver_fail(auth_client, driver_user):
    response = auth_client(driver_user).get(station_owners_list_url())

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "role_fixture",
    ["admin_user", "station_owner", "branch_manager", "station_worker"],
)
def test_list_allowed_roles_see_all_owners_success(
    role_fixture,
    request,
    auth_client,
    station,
    station_owner,
    other_station_owner,
):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture in {"station_owner", "branch_manager", "station_worker"}:
        client_kwargs["station_id"] = station.id

    response = auth_client(user, **client_kwargs).get(
        station_owners_list_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert {station_owner.id, other_station_owner.id}.issubset(ids)


def test_list_filter_by_station_success(
    auth_client, admin_user, station, station_owner, other_station_owner
):
    response = auth_client(admin_user).get(
        station_owners_list_url(station=station.id, no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert station_owner.id in ids
    assert other_station_owner.id not in ids


def test_list_search_by_phone_success(
    auth_client, admin_user, station_owner, other_station_owner
):
    response = auth_client(admin_user).get(
        station_owners_list_url(
            search=station_owner.phone_number, no_paginate="true"
        )
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert station_owner.id in ids
    assert other_station_owner.id not in ids


def test_list_payload_includes_nested_station_success(
    auth_client, admin_user, station_owner, station
):
    response = auth_client(admin_user).get(station_owners_list_url(no_paginate="true"))

    assert response.status_code == status.HTTP_200_OK
    listed = {item["id"]: item for item in response.data["results"]}
    row = listed[station_owner.id]
    assert row["name"] == station_owner.name
    assert row["role"] == User.UserRoles.StationOwner
    assert row["station"] == {"id": station.id, "name": station.name}
