from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Company


pytestmark = [pytest.mark.api, pytest.mark.django_db]


REQUIRED_FIELDS = ["name", "address"]


class TestCompanyCreate:


    def test_create_without_authentication_fail(self, api_client, company_payload_factory):
        response = api_client.post(
            reverse("companies-list"),
            company_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Company.objects.count() == 0


    @pytest.mark.parametrize(
        "role_fixture",
        [
            "admin_user",
            "finance_user",
            "company_owner",
            "station_worker",
        ],
    )
    def test_create_company_success(self,
        role_fixture,
        request,
        auth_client,
        company_payload_factory,
        geo_data,
        station,
    ):
        user = request.getfixturevalue(role_fixture)
        payload = company_payload_factory()
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = request.getfixturevalue("company").id
        if role_fixture == "station_worker":
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).post(
            reverse("companies-list"),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_company = Company.objects.get(name=payload["name"])
        assert created_company.email == payload["email"]
        assert created_company.phone_number == payload["phone_number"]
        assert created_company.address == payload["address"]
        assert created_company.district_id == geo_data["district"].id
        assert created_company.is_active is True
        assert created_company.balance == Decimal("0.00")
        assert created_company.created_by_id == user.id


    def test_create_without_optional_fields_success(self,
        auth_client, admin_user, company_payload_factory
    ):
        payload = company_payload_factory()
        payload.pop("email")
        payload.pop("phone_number")
        payload.pop("district")
        payload.pop("is_active")

        response = auth_client(admin_user).post(
            reverse("companies-list"),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_company = Company.objects.get(name=payload["name"])
        assert created_company.email is None
        assert created_company.phone_number is None
        assert created_company.district_id is None
        assert created_company.is_active is True
        assert created_company.created_by_id == admin_user.id


    def test_create_inactive_company_success(self,
        auth_client, admin_user, company_payload_factory
    ):
        payload = company_payload_factory(is_active=False)

        response = auth_client(admin_user).post(
            reverse("companies-list"),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_company = Company.objects.get(name=payload["name"])
        assert created_company.is_active is False


    def test_create_submitted_balance_ignored_success(self,
        auth_client, admin_user, company_payload_factory
    ):
        payload = company_payload_factory()
        payload["balance"] = "999.00"

        response = auth_client(admin_user).post(
            reverse("companies-list"),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_company = Company.objects.get(name=payload["name"])
        assert created_company.balance == Decimal("0.00")


    @pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
    def test_create_missing_required_field_fail(self,
        missing_field,
        auth_client,
        admin_user,
        company_payload_factory,
    ):
        payload = company_payload_factory()
        payload.pop(missing_field)
        existing_ids = set(Company.objects.values_list("id", flat=True))

        response = auth_client(admin_user).post(
            reverse("companies-list"),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert set(Company.objects.values_list("id", flat=True)) == existing_ids


    @pytest.mark.parametrize(
        ("field", "invalid_value"),
        [
            ("email", "not-an-email"),
            ("phone_number", "010000000001"),
            ("district", 999_999),
            ("name", "N" * 256),
            ("address", "A" * 256),
        ],
    )
    def test_create_invalid_field_fail(self,
        field,
        invalid_value,
        auth_client,
        admin_user,
        company_payload_factory,
    ):
        payload = company_payload_factory(**{field: invalid_value})
        existing_ids = set(Company.objects.values_list("id", flat=True))

        response = auth_client(admin_user).post(
            reverse("companies-list"),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert set(Company.objects.values_list("id", flat=True)) == existing_ids
