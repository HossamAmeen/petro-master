import pytest
from django.urls import reverse
from rest_framework import status

from apps.users.tests.helpers import station_owners_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]

SENSITIVE_FIELDS = ["password", "reset_password_token", "reset_password_token_created_at"]


class TestStationTenantIsolation:
    def test_owner_cannot_retrieve_another_station_fail(
        self, auth_client, station_owner, station_factory
    ):
        other = station_factory()

        response = auth_client(station_owner, station_id=station_owner.station_id).get(
            reverse("stations-detail", args=[other.id])
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_owner_can_retrieve_own_station_success(self, auth_client, station_owner):
        response = auth_client(station_owner, station_id=station_owner.station_id).get(
            reverse("stations-detail", args=[station_owner.station_id])
        )

        assert response.status_code == status.HTTP_200_OK

    def test_owner_cannot_update_another_station_fail(
        self, auth_client, station_owner, station_factory
    ):
        other = station_factory()

        response = auth_client(station_owner, station_id=station_owner.station_id).patch(
            reverse("stations-detail", args=[other.id]), {"name": "x"}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestStationOwnerListHidesSecrets:
    def test_list_never_exposes_password_fields_success(
        self, auth_client, station_owner
    ):
        response = auth_client(station_owner, station_id=station_owner.station_id).get(
            station_owners_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        for row in response.data["results"]:
            for field in SENSITIVE_FIELDS:
                assert field not in row
