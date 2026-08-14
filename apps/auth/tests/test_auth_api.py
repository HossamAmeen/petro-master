import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import AccessToken

from apps.companies.factories import CompanyUserFactory, UserFactory
from apps.users.models import User


@pytest.mark.api
@pytest.mark.django_db
class TestAuthenticationAPI:
    def test_company_login_returns_company_claims(self, api_client, company):
        owner = CompanyUserFactory(
            company=company,
            role=User.UserRoles.CompanyOwner,
        )

        response = api_client.post(
            reverse("company_login"),
            {"identifier": owner.email, "password": "password123"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["company_id"] == company.id
        access_token = AccessToken(response.data["access"])
        assert access_token["company_id"] == company.id
        assert access_token["role"] == User.UserRoles.CompanyOwner

    def test_company_login_rejects_dashboard_user(self, api_client):
        dashboard_user = UserFactory(role=User.UserRoles.Admin)

        response = api_client.post(
            reverse("company_login"),
            {"identifier": dashboard_user.email, "password": "password123"},
            format="json",
        )

        assert response.status_code == 401

    def test_profile_returns_authenticated_user(
        self, auth_client, company_owner, company
    ):
        client = auth_client(company_owner, company_id=company.id)

        response = client.get(reverse("profile"))

        assert response.status_code == 200
        assert response.data["id"] == company_owner.id
        assert response.data["balance"] == company.balance

    def test_profile_updates_password(self, auth_client, company_owner, company):
        client = auth_client(company_owner, company_id=company.id)

        response = client.patch(
            reverse("profile"),
            {"password": "a-new-password"},
            format="json",
        )

        assert response.status_code == 200
        company_owner.refresh_from_db()
        assert company_owner.check_password("a-new-password")

    def test_password_reset_sends_email_for_active_user(self, api_client):
        user = UserFactory()

        response = api_client.post(
            reverse("password_reset_request"),
            {"email": user.email},
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.reset_password_token
