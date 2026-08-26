import pytest
from rest_framework import status

from apps.users.models import StationOwner, User
from apps.users.tests.helpers import station_owners_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_create_without_authentication_fail(
    api_client, station_owner_payload_factory
):
    response = api_client.post(
        station_owners_list_url(),
        station_owner_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_as_company_owner_fail(
    auth_client, company_owner, company, station_owner_payload_factory
):
    before = StationOwner.objects.count()

    response = auth_client(company_owner, company_id=company.id).post(
        station_owners_list_url(),
        station_owner_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert StationOwner.objects.count() == before


def test_create_as_dashboard_success(
    auth_client, admin_user, station, station_owner_payload_factory
):
    payload = station_owner_payload_factory()

    response = auth_client(admin_user).post(
        station_owners_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = StationOwner.objects.get(phone_number=payload["phone_number"])
    assert created.name == payload["name"]
    assert created.station_id == station.id
    assert created.role == User.UserRoles.StationOwner


def test_create_as_station_owner_success(
    auth_client, station_owner, station, station_owner_payload_factory
):
    payload = station_owner_payload_factory()

    response = auth_client(station_owner, station_id=station.id).post(
        station_owners_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = StationOwner.objects.get(phone_number=payload["phone_number"])
    assert created.station_id == station.id


def test_create_missing_station_fail(
    auth_client, admin_user, station_owner_payload_factory
):
    payload = station_owner_payload_factory()
    payload.pop("station")
    before = StationOwner.objects.count()

    response = auth_client(admin_user).post(
        station_owners_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert StationOwner.objects.count() == before
