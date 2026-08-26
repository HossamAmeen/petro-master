import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import returned_ids, user_ref, users_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestUserList:


    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(users_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    @pytest.mark.parametrize(
        "role_fixture",
        [
            "finance_user",
            "customer_support_user",
            "company_owner",
            "station_owner",
            "station_worker",
            "driver_user",
        ],
    )
    def test_list_non_admin_fail(self, role_fixture, request, auth_client, company, station):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture in {"company_owner"}:
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker"}:
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).get(users_list_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN


    def test_list_dashboard_users_success(self,
        auth_client,
        admin_user,
        finance_user,
        customer_support_user,
        company_owner,
        station_owner,
        driver_user,
    ):
        response = auth_client(admin_user).get(users_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert {admin_user.id, finance_user.id, customer_support_user.id}.issubset(ids)
        assert company_owner.id not in ids
        assert station_owner.id not in ids
        assert driver_user.id not in ids


    def test_list_includes_audit_fields_success(self, auth_client, admin_user, finance_user):
        response = auth_client(admin_user).get(users_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[finance_user.id]
        assert row["name"] == finance_user.name
        assert row["email"] == finance_user.email
        assert row["phone_number"] == finance_user.phone_number
        assert row["role"] == User.UserRoles.Finance
        assert row["is_active"] is True
        assert row["created_by"] == user_ref(admin_user)
        assert "password" not in row


    def test_list_filter_by_role_success(self,
        auth_client, admin_user, finance_user, customer_support_user
    ):
        response = auth_client(admin_user).get(
            users_list_url(role=User.UserRoles.Finance, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert finance_user.id in ids
        assert admin_user.id not in ids
        assert customer_support_user.id not in ids


    def test_list_filter_by_is_active_success(self,
        auth_client, admin_user, finance_user, inactive_finance_user
    ):
        response = auth_client(admin_user).get(
            users_list_url(is_active="false", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert inactive_finance_user.id in ids
        assert finance_user.id not in ids
