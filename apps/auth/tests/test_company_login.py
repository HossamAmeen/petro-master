import pytest
from rest_framework import status

from apps.auth.tests.helpers import (
    LOGIN_PASSWORD,
    company_login_url,
    decode_access,
    decode_refresh,
    login_payload,
    set_login_password,
)
from apps.users.models import CompanyUser, User


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _login(api_client, user, **payload_kwargs):
    set_login_password(user)
    return api_client.post(
        company_login_url(),
        login_payload(user, **payload_kwargs),
        format="json",
    )


class TestCompanyLogin:


    @pytest.mark.parametrize(
        "role_fixture",
        ["company_owner", "company_branch_manager"],
    )
    def test_company_login_with_email_success(self,
        role_fixture,
        request,
        api_client,
        company,
        company_branch,
        second_company_branch,
    ):
        user = request.getfixturevalue(role_fixture)

        response = _login(api_client, user)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["user_name"] == user.name
        assert response.data["role"] == user.role
        assert response.data["company_id"] == company.id
        assert response.data["user"] == {
            "id": user.id,
            "name": user.name,
            "role": user.role,
        }
        assert set(response.data["branches"]) == {
            company_branch.id,
            second_company_branch.id,
        }
        access = decode_access(response.data["access"])
        refresh = decode_refresh(response.data["refresh"])
        assert access["user_name"] == user.name
        assert access["role"] == user.role
        assert access["company_id"] == company.id
        assert refresh["user_name"] == user.name
        assert refresh["role"] == user.role
        assert refresh["company_id"] == company.id


    def test_company_login_with_phone_number_success(self, api_client, company_owner, company):
        response = _login(api_client, company_owner, identifier=company_owner.phone_number)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["company_id"] == company.id
        assert decode_access(response.data["access"])["company_id"] == company.id


    def test_company_login_without_branches_success(self, api_client, company_owner, company):
        response = _login(api_client, company_owner)

        assert response.status_code == status.HTTP_200_OK, response.data
        assert list(response.data["branches"]) == []
        assert response.data["company_id"] == company.id


    @pytest.mark.parametrize("missing_field", ["identifier", "password"])
    def test_company_login_missing_field_fail(self, api_client, company_owner, missing_field):
        set_login_password(company_owner)
        payload = login_payload(company_owner)
        payload.pop(missing_field)

        response = api_client.post(company_login_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "validation_error"


    def test_company_login_empty_identifier_fail(self, api_client, company_owner):
        response = _login(api_client, company_owner, identifier="")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "validation_error"


    def test_company_login_wrong_password_fail(self, api_client, company_owner):
        response = _login(api_client, company_owner, password="wrong-password")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"
        assert response.data["message"] == "Invalid credentials"


    def test_company_login_unknown_identifier_fail(self, api_client):
        response = api_client.post(
            company_login_url(),
            {"identifier": "nobody@example.com", "password": LOGIN_PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"


    def test_company_login_inactive_user_fail(self, api_client, admin_user, company):
        owner = CompanyUser.objects.create(
            name="Inactive Owner",
            phone_number="01000000990",
            email="inactive-owner@example.com",
            password="placeholder",
            role=User.UserRoles.CompanyOwner,
            company=company,
            created_by=admin_user,
            is_active=False,
        )
        set_login_password(owner)

        response = api_client.post(
            company_login_url(),
            login_payload(owner),
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
            "station_owner",
            "branch_manager",
            "station_worker",
            "driver_user",
            "supervisor",
            "agent",
        ],
    )
    def test_company_login_wrong_role_fail(self, role_fixture, request, api_client):
        user = request.getfixturevalue(role_fixture)

        response = _login(api_client, user)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"


    def test_company_login_get_method_fail(self, api_client):
        response = api_client.get(company_login_url())

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
