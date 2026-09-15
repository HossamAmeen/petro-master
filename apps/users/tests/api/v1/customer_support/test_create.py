import pytest
from rest_framework import status

from apps.users.models import CustomerSupport, User
from apps.users.tests.helpers import customer_support_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]

NON_ADMIN_ROLES = [
    "finance_user",
    "customer_support_user",
    "company_owner",
    "company_branch_manager",
    "station_owner",
    "branch_manager",
    "station_worker",
]
REQUIRED_FIELDS = ["name", "email", "phone_number", "password", "confirm_password"]


class TestCustomerSupportCreate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, customer_support_payload_factory):
        self.admin = admin_user
        self.client = auth_client(admin_user)
        self.payload_factory = customer_support_payload_factory
        self.url = customer_support_list_url()

    def test_create_success(self):
        payload = self.payload_factory()

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CustomerSupport.objects.get(phone_number=payload["phone_number"])
        assert response.data == {
            "id": created.id,
            "name": payload["name"],
            "email": payload["email"],
            "phone_number": payload["phone_number"],
            "is_active": True,
        }
        assert created.role == User.UserRoles.CustomerSupport
        assert created.check_password("password123")
        assert created.created_by_id == self.admin.id

    def test_create_ignores_a_submitted_role_success(self):
        payload = self.payload_factory(role=User.UserRoles.Admin)

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = User.objects.get(phone_number=payload["phone_number"])
        assert created.role == User.UserRoles.CustomerSupport
        assert created.is_superuser is False

    def test_create_inactive_success(self):
        payload = self.payload_factory(is_active=False)

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert not User.objects.get(phone_number=payload["phone_number"]).is_active

    def test_create_without_authentication_fail(self, api_client):
        response = api_client.post(self.url, self.payload_factory(), format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert not CustomerSupport.objects.exists()

    @pytest.mark.parametrize("role_fixture", NON_ADMIN_ROLES)
    def test_create_non_admin_fail(self, role_fixture, role_client):
        client = role_client(role_fixture)
        before = User.objects.count()

        response = client.post(self.url, self.payload_factory(), format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert User.objects.count() == before

    def test_create_password_mismatch_fail(self):
        payload = self.payload_factory(confirm_password="other-pass")

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "Passwords do not match"
        assert not CustomerSupport.objects.exists()

    @pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
    def test_create_missing_required_field_fail(self, missing_field):
        payload = self.payload_factory()
        payload.pop(missing_field)

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CustomerSupport.objects.exists()

    def test_create_duplicate_phone_fail(self, finance_user):
        payload = self.payload_factory(phone_number=finance_user.phone_number)

        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CustomerSupport.objects.exists()
