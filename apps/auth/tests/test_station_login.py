import pytest
from rest_framework import status

from apps.auth.tests.helpers import (
    LOGIN_PASSWORD,
    decode_access,
    decode_refresh,
    login_payload,
    set_login_password,
    station_login_url,
)
from apps.users.models import StationOwner, User, Worker


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _login(api_client, user, **payload_kwargs):
    set_login_password(user)
    return api_client.post(
        station_login_url(),
        login_payload(user, **payload_kwargs),
        format="json",
    )


class TestStationLogin:


    @pytest.mark.parametrize(
        "role_fixture",
        ["station_owner", "branch_manager", "station_worker"],
    )
    def test_station_login_with_email_success(self, role_fixture, request, api_client, station):
        user = request.getfixturevalue(role_fixture)

        response = _login(api_client, user)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["user_name"] == user.name
        assert response.data["role"] == user.role
        assert response.data["station_id"] == station.id
        assert "company_id" not in response.data
        access = decode_access(response.data["access"])
        refresh = decode_refresh(response.data["refresh"])
        assert access["user_name"] == user.name
        assert access["role"] == user.role
        assert access["station_id"] == station.id
        assert refresh["user_name"] == user.name
        assert refresh["role"] == user.role
        assert refresh["station_id"] == station.id


    def test_station_login_with_phone_number_success(self, api_client, station_owner, station):
        response = _login(
            api_client, station_owner, identifier=station_owner.phone_number
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["station_id"] == station.id
        assert decode_access(response.data["access"])["station_id"] == station.id


    def test_station_worker_login_uses_branch_station_success(self,
        api_client, station_worker, station
    ):
        response = _login(api_client, station_worker)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["station_id"] == station_worker.station_branch.station_id
        assert response.data["station_id"] == station.id


    @pytest.mark.parametrize("missing_field", ["identifier", "password"])
    def test_station_login_missing_field_fail(self, api_client, station_owner, missing_field):
        set_login_password(station_owner)
        payload = login_payload(station_owner)
        payload.pop(missing_field)

        response = api_client.post(station_login_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "validation_error"


    def test_station_login_wrong_password_fail(self, api_client, station_owner):
        response = _login(api_client, station_owner, password="wrong-password")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"
        assert response.data["message"] == "Invalid credentials"


    def test_station_login_unknown_identifier_fail(self, api_client):
        response = api_client.post(
            station_login_url(),
            {"identifier": "nobody@example.com", "password": LOGIN_PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"


    def test_station_login_inactive_owner_fail(self, api_client, admin_user, station):
        owner = StationOwner.objects.create(
            name="Inactive Station Owner",
            phone_number="01000000991",
            email="inactive-station-owner@example.com",
            password="placeholder",
            role=User.UserRoles.StationOwner,
            station=station,
            created_by=admin_user,
            is_active=False,
        )
        set_login_password(owner)

        response = api_client.post(
            station_login_url(),
            login_payload(owner),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"


    def test_station_login_inactive_worker_fail(self, api_client, admin_user, branch):
        worker = Worker.objects.create(
            name="Inactive Worker",
            phone_number="01000000992",
            email="inactive-worker@example.com",
            password="placeholder",
            role=User.UserRoles.StationWorker,
            station_branch=branch,
            created_by=admin_user,
            is_active=False,
        )
        set_login_password(worker)

        response = api_client.post(
            station_login_url(),
            login_payload(worker),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"


    @pytest.mark.parametrize(
        "role_fixture",
        [
            "admin_user",
            "finance_user",
            "customer_support_user",
            "company_owner",
            "company_branch_manager",
            "driver_user",
            "supervisor",
            "agent",
        ],
    )
    def test_station_login_wrong_role_fail(self, role_fixture, request, api_client):
        user = request.getfixturevalue(role_fixture)

        response = _login(api_client, user)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"


    def test_station_login_get_method_fail(self, api_client):
        response = api_client.get(station_login_url())

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
