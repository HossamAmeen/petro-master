from decimal import Decimal

import pytest
from rest_framework import status

from apps.auth.tests.helpers import (
    LOGIN_PASSWORD,
    company_login_url,
    login_payload,
    profile_url,
    set_login_password,
)
from apps.stations.models.stations_models import StationBranch
from apps.users.models import User

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestProfile:

    def test_profile_without_authentication_fail(self, api_client):
        response = api_client.get(profile_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_profile_update_without_authentication_fail(self, api_client):
        response = api_client.patch(
            profile_url(),
            {"name": "Hacker"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_profile_company_owner_returns_company_balance_success(
        self, auth_client, company_owner, company
    ):
        company.balance = Decimal("150.50")
        company.save(update_fields=["balance"])

        response = auth_client(company_owner, company_id=company.id).get(profile_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_owner.id
        assert response.data["name"] == company_owner.name
        assert response.data["email"] == company_owner.email
        assert response.data["phone_number"] == company_owner.phone_number
        assert response.data["role"] == User.UserRoles.CompanyOwner
        assert response.data["balance"] == company.balance
        assert response.data["available_balance"] == 0
        assert "password" not in response.data

    def test_profile_company_branch_manager_sums_managed_branch_balances_success(
        self,
        auth_client,
        company_branch_manager,
        company,
        company_branch,
        second_company_branch,
    ):
        company_branch.balance = Decimal("80.00")
        company_branch.save(update_fields=["balance"])
        second_company_branch.balance = Decimal("40.00")
        second_company_branch.save(update_fields=["balance"])
        company.balance = Decimal("999.00")
        company.save(update_fields=["balance"])

        response = auth_client(company_branch_manager, company_id=company.id).get(
            profile_url()
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_branch_manager.id
        assert response.data["balance"] == Decimal("80.00")
        assert response.data["available_balance"] == 0

    def test_profile_station_owner_returns_station_balance_success(
        self, auth_client, station_owner, station
    ):
        station.balance = Decimal("220.00")
        station.save(update_fields=["balance"])

        response = auth_client(station_owner, station_id=station.id).get(profile_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == station_owner.id
        assert response.data["role"] == User.UserRoles.StationOwner
        assert response.data["balance"] == station.balance
        assert response.data["available_balance"] == 0

    def test_profile_station_branch_manager_sums_managed_branch_balances_success(
        self,
        auth_client,
        admin_user,
        branch_manager,
        station,
        branch,
        geo_data,
    ):
        branch.balance = Decimal("55.00")
        branch.save(update_fields=["balance"])
        StationBranch.objects.create(
            name="Unmanaged Station Branch",
            address="Other Address",
            lang=31.2357,
            lat=30.0444,
            district=geo_data["district"],
            station=station,
            created_by=admin_user,
            balance=Decimal("90.00"),
        )
        station.balance = Decimal("500.00")
        station.save(update_fields=["balance"])

        response = auth_client(branch_manager, station_id=station.id).get(profile_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["balance"] == Decimal("55.00")
        assert response.data["available_balance"] == 0

    def test_profile_station_worker_balance_is_zero_success(
        self, auth_client, station_worker, station, branch
    ):
        station.balance = Decimal("300.00")
        station.save(update_fields=["balance"])
        branch.balance = Decimal("75.00")
        branch.save(update_fields=["balance"])

        response = auth_client(station_worker, station_id=station.id).get(profile_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == station_worker.id
        assert response.data["role"] == User.UserRoles.StationWorker
        assert response.data["balance"] == 0
        assert response.data["available_balance"] == 0

    @pytest.mark.parametrize(
        "role_fixture",
        ["admin_user", "finance_user", "customer_support_user"],
    )
    def test_profile_dashboard_user_omits_role_balance_success(
        self, role_fixture, request, auth_client
    ):
        user = request.getfixturevalue(role_fixture)

        response = auth_client(user).get(profile_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == user.id
        assert "balance" not in response.data
        assert response.data["available_balance"] == 0
        assert "password" not in response.data

    def test_profile_updates_name_and_email_success(
        self, auth_client, company_owner, company
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            profile_url(),
            {"name": "Updated Owner", "email": "updated-owner@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        company_owner.refresh_from_db()
        assert company_owner.name == "Updated Owner"
        assert company_owner.email == "updated-owner@example.com"
        assert response.data["name"] == "Updated Owner"
        assert response.data["email"] == "updated-owner@example.com"

    def test_profile_updates_password_success(
        self, auth_client, api_client, company_owner, company
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            profile_url(),
            {"password": "a-new-password"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "password" not in response.data
        company_owner.refresh_from_db()
        assert company_owner.check_password("a-new-password")
        assert not company_owner.check_password(LOGIN_PASSWORD)

        login_response = api_client.post(
            company_login_url(),
            login_payload(company_owner, password="a-new-password"),
            format="json",
        )
        assert login_response.status_code == status.HTTP_200_OK, login_response.data

    def test_profile_put_updates_writable_fields_success(
        self, auth_client, company_owner, company
    ):
        response = auth_client(company_owner, company_id=company.id).put(
            profile_url(),
            {
                "name": "Put Owner",
                "email": "put-owner@example.com",
                "password": "put-password-1",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_owner.refresh_from_db()
        assert company_owner.name == "Put Owner"
        assert company_owner.email == "put-owner@example.com"
        assert company_owner.check_password("put-password-1")

    def test_profile_ignores_read_only_phone_and_role_success(
        self, auth_client, company_owner, company
    ):
        original_phone = company_owner.phone_number

        response = auth_client(company_owner, company_id=company.id).patch(
            profile_url(),
            {
                "phone_number": "01999999999",
                "role": User.UserRoles.Admin,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        company_owner.refresh_from_db()
        assert company_owner.phone_number == original_phone
        assert company_owner.role == User.UserRoles.CompanyOwner
        assert response.data["phone_number"] == original_phone
        assert response.data["role"] == User.UserRoles.CompanyOwner

    def test_profile_empty_patch_success(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).patch(
            profile_url(),
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_owner.id

    def test_profile_post_method_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).post(
            profile_url(),
            {"name": "Nope"},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
