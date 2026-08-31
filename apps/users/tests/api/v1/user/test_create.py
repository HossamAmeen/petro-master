import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import users_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


REQUIRED_FIELDS = ["name", "phone_number", "password", "confirm_password"]


class TestUserCreate:


    def test_create_without_authentication_fail(self, api_client, dashboard_user_payload_factory):
        payload = dashboard_user_payload_factory()

        response = api_client.post(
            users_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not User.objects.filter(phone_number=payload["phone_number"]).exists()


    @pytest.mark.parametrize("role_fixture", ["finance_user", "company_owner", "station_owner"])
    def test_create_non_admin_fail(self,
        role_fixture,
        request,
        auth_client,
        company,
        station,
        dashboard_user_payload_factory,
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture == "station_owner":
            client_kwargs["station_id"] = station.id
        before = User.objects.count()

        response = auth_client(user, **client_kwargs).post(
            users_list_url(),
            dashboard_user_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert User.objects.count() == before


    def test_create_dashboard_user_success(self,
        auth_client, admin_user, dashboard_user_payload_factory
    ):
        payload = dashboard_user_payload_factory()

        response = auth_client(admin_user).post(users_list_url(), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = User.objects.get(phone_number=payload["phone_number"])
        assert created.name == payload["name"]
        assert created.email == payload["email"]
        assert created.role == User.UserRoles.Finance
        assert created.check_password("password123")
        assert created.created_by_id == admin_user.id
        assert "password" not in response.data


    def test_create_without_email_fail(self,
        auth_client, admin_user, dashboard_user_payload_factory
    ):
        payload = dashboard_user_payload_factory()
        payload.pop("email")
        before = User.objects.count()

        response = auth_client(admin_user).post(users_list_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == before


    def test_create_password_mismatch_fail(self,
        auth_client, admin_user, dashboard_user_payload_factory
    ):
        payload = dashboard_user_payload_factory(confirm_password="other-pass")
        before = User.objects.count()

        response = auth_client(admin_user).post(users_list_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == before


    @pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
    def test_create_missing_required_field_fail(self,
        missing_field,
        auth_client,
        admin_user,
        dashboard_user_payload_factory,
    ):
        payload = dashboard_user_payload_factory()
        payload.pop(missing_field)
        before = User.objects.count()

        response = auth_client(admin_user).post(users_list_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == before


    def test_create_duplicate_phone_fail(self,
        auth_client, admin_user, finance_user, dashboard_user_payload_factory
    ):
        payload = dashboard_user_payload_factory(phone_number=finance_user.phone_number)
        before = User.objects.count()

        response = auth_client(admin_user).post(users_list_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == before
