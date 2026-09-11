import pytest
from django.conf import settings
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auth.tests.helpers import (
    company_login_url,
    company_refresh_for,
    decode_access,
    login_payload,
    set_login_password,
    station_refresh_for,
    token_refresh_url,
)
from apps.users.models import User

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestTokenRefresh:

    def test_token_refresh_company_preserves_company_id_success(
        self, api_client, company_owner, company
    ):
        refresh = company_refresh_for(company_owner, company.id)

        response = api_client.post(
            token_refresh_url(),
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        access = decode_access(response.data["access"])
        assert access["company_id"] == company.id
        assert access["role"] == User.UserRoles.CompanyOwner

    def test_token_refresh_station_preserves_station_id_success(
        self, api_client, station_owner, station
    ):
        refresh = station_refresh_for(station_owner, station.id)

        response = api_client.post(
            token_refresh_url(),
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        access = decode_access(response.data["access"])
        assert access["station_id"] == station.id
        assert access["role"] == User.UserRoles.StationOwner

    @pytest.mark.parametrize(
        "role_fixture",
        ["station_owner", "branch_manager", "station_worker"],
    )
    def test_token_refresh_station_roles_success(
        self, role_fixture, request, api_client, station
    ):
        user = request.getfixturevalue(role_fixture)
        refresh = station_refresh_for(user, station.id)

        response = api_client.post(
            token_refresh_url(),
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert decode_access(response.data["access"])["station_id"] == station.id

    def test_token_refresh_dashboard_success(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)

        response = api_client.post(
            token_refresh_url(),
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["access"]
        access = decode_access(response.data["access"])
        assert "company_id" not in access
        assert "station_id" not in access

    def test_token_refresh_after_company_login_success(
        self, api_client, company_owner, company, company_branch
    ):
        set_login_password(company_owner)
        login_response = api_client.post(
            company_login_url(),
            login_payload(company_owner),
            format="json",
        )
        assert login_response.status_code == status.HTTP_200_OK, login_response.data

        response = api_client.post(
            token_refresh_url(),
            {"refresh": login_response.data["refresh"]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        access = decode_access(response.data["access"])
        assert access["company_id"] == company.id

    def test_token_refresh_company_missing_company_id_fail(
        self, api_client, company_owner
    ):
        refresh = RefreshToken.for_user(company_owner)
        refresh["role"] = User.UserRoles.CompanyOwner

        response = api_client.post(
            token_refresh_url(),
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Company ID required" in str(response.data)

    def test_token_refresh_station_missing_station_id_fail(
        self, api_client, station_owner
    ):
        refresh = RefreshToken.for_user(station_owner)
        refresh["role"] = User.UserRoles.StationOwner

        response = api_client.post(
            token_refresh_url(),
            {"refresh": str(refresh)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Station ID required" in str(response.data)

    def test_token_refresh_invalid_token_fail(self, api_client):
        response = api_client.post(
            token_refresh_url(),
            {"refresh": "not-a-jwt"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_missing_refresh_fail(self, api_client):
        response = api_client.post(token_refresh_url(), {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_refresh_access_token_rejected_fail(
        self, api_client, company_owner, company
    ):
        refresh = company_refresh_for(company_owner, company.id)
        access = str(refresh.access_token)

        response = api_client.post(
            token_refresh_url(),
            {"refresh": access},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_rotated_refresh_success(
        self, api_client, company_owner, company
    ):
        if not settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
            pytest.skip("Refresh-token rotation is disabled")

        refresh = company_refresh_for(company_owner, company.id)
        first = api_client.post(
            token_refresh_url(),
            {"refresh": str(refresh)},
            format="json",
        )
        assert first.status_code == status.HTTP_200_OK, first.data
        assert "refresh" in first.data

        response = api_client.post(
            token_refresh_url(),
            {"refresh": first.data["refresh"]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["access"]

    def test_token_refresh_get_method_fail(self, api_client):
        response = api_client.get(token_refresh_url())

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
