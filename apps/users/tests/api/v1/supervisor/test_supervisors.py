import pytest
from rest_framework import status

from apps.users.models import Supervisor, User
from apps.users.tests.helpers import (
    returned_ids,
    supervisors_detail_url,
    supervisors_list_url,
    user_ref,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestSupervisors:

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(supervisors_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        ["finance_user", "company_owner", "station_owner"],
    )
    def test_list_non_admin_fail(
        self, role_fixture, request, auth_client, company, station
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture == "station_owner":
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).get(supervisors_list_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_success(self, auth_client, admin_user, supervisor, geo_data):
        response = auth_client(admin_user).get(supervisors_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        assert supervisor.id in returned_ids(response)
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[supervisor.id]
        assert row["name"] == supervisor.name
        assert row["role"] == User.UserRoles.Supervisor
        assert row["created_by"] == user_ref(admin_user)
        assert any(item["id"] == geo_data["district"].id for item in row["district"])

    def test_create_without_authentication_fail(
        self, api_client, supervisor_payload_factory
    ):
        response = api_client.post(
            supervisors_list_url(),
            supervisor_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_as_finance_fail(
        self, auth_client, finance_user, supervisor_payload_factory
    ):
        before = Supervisor.objects.count()

        response = auth_client(finance_user).post(
            supervisors_list_url(),
            supervisor_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Supervisor.objects.count() == before

    def test_create_success(
        self, auth_client, admin_user, geo_data, supervisor_payload_factory
    ):
        payload = supervisor_payload_factory()

        response = auth_client(admin_user).post(
            supervisors_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = Supervisor.objects.get(phone_number=payload["phone_number"])
        assert created.name == payload["name"]
        assert created.role == User.UserRoles.Supervisor
        assert created.check_password("password123")
        assert created.created_by_id == admin_user.id
        assert list(created.district.values_list("id", flat=True)) == [
            geo_data["district"].id
        ]

    def test_create_password_mismatch_fail(
        self, auth_client, admin_user, supervisor_payload_factory
    ):
        payload = supervisor_payload_factory(confirm_password="other-pass")
        before = Supervisor.objects.count()

        response = auth_client(admin_user).post(
            supervisors_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Supervisor.objects.count() == before

    def test_create_missing_district_fail(
        self, auth_client, admin_user, supervisor_payload_factory
    ):
        payload = supervisor_payload_factory()
        payload.pop("district")
        before = Supervisor.objects.count()

        response = auth_client(admin_user).post(
            supervisors_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Supervisor.objects.count() == before

    def test_retrieve_success(self, auth_client, admin_user, supervisor, geo_data):
        response = auth_client(admin_user).get(supervisors_detail_url(supervisor.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == supervisor.id
        assert response.data["name"] == supervisor.name
        assert any(
            item["id"] == geo_data["district"].id for item in response.data["district"]
        )

    def test_update_name_success(self, auth_client, admin_user, supervisor):
        response = auth_client(admin_user).patch(
            supervisors_detail_url(supervisor.id),
            {"name": "Updated Supervisor"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        supervisor.refresh_from_db()
        assert supervisor.name == "Updated Supervisor"
        assert supervisor.updated_by_id == admin_user.id

    def test_update_password_mismatch_fail(self, auth_client, admin_user, supervisor):
        response = auth_client(admin_user).patch(
            supervisors_detail_url(supervisor.id),
            {"password": "new-pass-123", "confirm_password": "other-pass"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_as_finance_fail(self, auth_client, finance_user, supervisor):
        response = auth_client(finance_user).delete(
            supervisors_detail_url(supervisor.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Supervisor.objects.filter(pk=supervisor.id).exists()

    def test_delete_success(self, auth_client, admin_user, supervisor):
        user_id = supervisor.id

        response = auth_client(admin_user).delete(supervisors_detail_url(user_id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Supervisor.objects.filter(pk=user_id).exists()
