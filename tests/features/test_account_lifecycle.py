"""A user logs in, keeps the session alive, edits the profile and resets a
forgotten password.

Each test follows the Given-When-Then template. These tests own their own
arrangement (there is no shared ``setup`` fixture) so the Given is inline.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework import status

from apps.auth.tests.helpers import (
    LOGIN_PASSWORD,
    decode_access,
    password_reset_confirm_url,
    password_reset_request_url,
    profile_url,
    set_login_password,
    token_refresh_url,
)
from apps.stations.tests.helpers import home_url as station_home_url
from apps.users.models import User
from apps.users.tests.helpers import company_owners_detail_url

from .helpers import bearer_client, company_home_url, login, sign_in

pytestmark = [pytest.mark.django_db, pytest.mark.feature]

NEW_PASSWORD = "brand-new-pass"


class TestAccountLifecycle:
    def refresh(self, api_client, login_response):
        return api_client.post(
            token_refresh_url(),
            {"refresh": login_response.data["refresh"]},
            format="json",
        )

    def test_company_session_survives_a_token_refresh_success(
        self, api_client, company, company_owner
    ):
        # Given a logged-in company owner
        set_login_password(company_owner)

        # When the access token is refreshed and used
        refreshed = self.refresh(api_client, login("company", company_owner))
        home = bearer_client(refreshed.data["access"]).get(company_home_url())

        # Then the company claim is preserved and the session still works
        assert refreshed.status_code == status.HTTP_200_OK, refreshed.data
        assert decode_access(refreshed.data["access"])["company_id"] == company.id
        assert home.status_code == status.HTTP_200_OK
        assert home.data["name"] == company.name

    def test_station_session_survives_a_token_refresh_success(
        self, api_client, station, branch, station_worker
    ):
        # Given a logged-in station worker
        set_login_password(station_worker)

        # When the access token is refreshed and used
        refreshed = self.refresh(api_client, login("station", station_worker))
        home = bearer_client(refreshed.data["access"]).get(station_home_url())

        # Then the station claim is preserved and the session still works
        assert refreshed.status_code == status.HTTP_200_OK, refreshed.data
        assert decode_access(refreshed.data["access"])["station_id"] == station.id
        assert home.data["station_branch_id"] == branch.id

    def test_user_edits_profile_and_password_success(self, company_owner):
        # Given a signed-in company owner
        client = sign_in("company", company_owner)

        # When they patch their profile and password
        response = client.patch(
            profile_url(),
            {
                "name": "Renamed Owner",
                "phone_number": "01999999999",
                "role": User.UserRoles.Admin,
                "password": NEW_PASSWORD,
            },
            format="json",
        )

        # Then name/password change, phone and role stay, new password logs in
        assert response.status_code == status.HTTP_200_OK, response.data
        company_owner.refresh_from_db()
        assert company_owner.name == "Renamed Owner"
        # phone number and role are read-only
        assert company_owner.phone_number == "01000000005"
        assert company_owner.role == User.UserRoles.CompanyOwner
        assert login("company", company_owner).status_code == 401
        assert login("company", company_owner, NEW_PASSWORD).status_code == 200

    def test_forgotten_password_is_reset_by_email_success(
        self, api_client, company_owner
    ):
        # Given a user who has forgotten their password
        set_login_password(company_owner)

        # When they request a reset, open the link and set a new password twice
        requested = api_client.post(
            password_reset_request_url(), {"email": company_owner.email}, format="json"
        )
        company_owner.refresh_from_db()
        confirm_url = password_reset_confirm_url(company_owner.reset_password_token)
        form = api_client.get(confirm_url)
        reset = api_client.post(
            confirm_url,
            {"password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
            format="json",
        )
        reused = api_client.post(
            confirm_url,
            {"password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
            format="json",
        )

        # Then the email carries the link, the first reset works, reuse fails,
        # and only the new password logs in
        assert requested.status_code == status.HTTP_200_OK, requested.data
        (email,) = mail.outbox
        assert email.to == [company_owner.email]
        assert confirm_url in email.alternatives[0][0]
        assert form.status_code == status.HTTP_200_OK
        assert reset.status_code == status.HTTP_200_OK, reset.data
        assert reused.status_code == status.HTTP_400_BAD_REQUEST
        assert login("company", company_owner, NEW_PASSWORD).status_code == 200
        assert login("company", company_owner).status_code == 401

    def test_expired_reset_link_fail(self, api_client, company_owner):
        # Given a reset token issued over 24 hours ago
        set_login_password(company_owner)
        api_client.post(
            password_reset_request_url(), {"email": company_owner.email}, format="json"
        )
        company_owner.refresh_from_db()
        User.objects.filter(id=company_owner.id).update(
            reset_password_token_created_at=timezone.localtime() - timedelta(hours=25)
        )

        # When the user tries to set a new password with the stale token
        response = api_client.post(
            password_reset_confirm_url(company_owner.reset_password_token),
            {"password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
            format="json",
        )

        # Then it is rejected and the old password still works
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert login("company", company_owner).status_code == status.HTTP_200_OK

    def test_reset_for_a_phone_only_user_mails_the_placeholder_fail(
        self, api_client, company_owner
    ):
        """Open issue (TODO "Send forgot password"): users created without an
        email get `{phone}@petro.com`, so the reset link is mailed nowhere."""
        # Given a user whose email is the generated placeholder
        placeholder = f"{company_owner.phone_number}@petro.com"
        User.objects.filter(id=company_owner.id).update(email=placeholder)

        # When they request a password reset
        response = api_client.post(
            password_reset_request_url(), {"email": placeholder}, format="json"
        )

        # Then the reset link is mailed to the unreachable placeholder address
        assert response.status_code == status.HTTP_200_OK
        assert mail.outbox[0].to == [placeholder]

    @pytest.mark.parametrize(
        "user_fixture", ["admin_user", "finance_user", "customer_support_user"]
    )
    def test_dashboard_roles_log_in_to_the_dashboard_success(
        self, request, user_fixture
    ):
        # Given a dashboard-role user
        user = set_login_password(request.getfixturevalue(user_fixture))

        # When they log in at the dashboard endpoint
        response = login("dashboard", user)

        # Then login succeeds with their role
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["role"] == user.role

    @pytest.mark.parametrize(
        ("kind", "user_fixture", "password"),
        [
            ("company", "station_owner", LOGIN_PASSWORD),
            ("station", "company_owner", LOGIN_PASSWORD),
            ("dashboard", "company_owner", LOGIN_PASSWORD),
            ("dashboard", "station_worker", LOGIN_PASSWORD),
            ("company", "company_owner", "wrong-password"),
        ],
    )
    def test_wrong_role_or_password_fail(self, request, kind, user_fixture, password):
        # Given a user logging in at the wrong endpoint or with a bad password
        user = set_login_password(request.getfixturevalue(user_fixture))

        # When they attempt to log in
        response = login(kind, user, password)

        # Then it is rejected as invalid credentials
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["code"] == "invalid_credentials"

    def test_deactivated_user_cannot_log_in_fail(self, company_owner):
        # Given a deactivated owner (as done from the Django admin)
        set_login_password(company_owner)
        User.objects.filter(id=company_owner.id).update(is_active=False)

        # When they try to log in
        response = login("company", company_owner)

        # Then login is refused
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_cannot_deactivate_an_owner_through_the_api_fail(
        self, admin_user, company_owner
    ):
        """Open issue: the company-owner serializer has no `is_active`, so the
        PATCH succeeds but the owner stays active and can still log in."""
        # Given a signed-in dashboard admin and an active owner
        set_login_password(company_owner)
        admin = sign_in("dashboard", admin_user)

        # When the admin PATCHes the owner to inactive
        response = admin.patch(
            company_owners_detail_url(company_owner.id),
            {"is_active": False, "company_id": company_owner.company_id},
            format="json",
        )

        # Then the PATCH "succeeds" but the owner stays active and can log in
        assert response.status_code == status.HTTP_200_OK, response.data
        company_owner.refresh_from_db()
        assert company_owner.is_active is True
        assert login("company", company_owner).status_code == status.HTTP_200_OK
