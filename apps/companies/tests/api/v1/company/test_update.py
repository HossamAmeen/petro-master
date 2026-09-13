from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def company_detail_url(company_id):
    return reverse("companies-detail", kwargs={"pk": company_id})


class TestCompanyUpdate:

    def test_partial_update_without_authentication_fail(self, api_client, company):
        response = api_client.patch(
            company_detail_url(company.id),
            {"name": "Updated Company"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_partial_update_company_success(
        self,
        auth_client,
        admin_user,
        company,
    ):
        response = auth_client(admin_user).patch(
            company_detail_url(company.id),
            {"name": "Updated Company"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company.refresh_from_db()
        assert company.name == "Updated Company"
        assert company.updated_by_id == admin_user.id

    def test_partial_update_deactivate_success(self, auth_client, admin_user, company):
        response = auth_client(admin_user).patch(
            company_detail_url(company.id),
            {"is_active": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company.refresh_from_db()
        assert company.is_active is False

    def test_partial_update_other_company_as_company_owner_success(
        self,
        auth_client,
        company_owner,
        company,
        other_company,
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            company_detail_url(other_company.id),
            {"name": "Renamed Other Company"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        other_company.refresh_from_db()
        assert other_company.name == "Renamed Other Company"
        assert other_company.updated_by_id == company_owner.id

    @pytest.mark.parametrize(
        ("restricted_field", "new_value"),
        [
            ("balance", "999.00"),
            ("created_by", 999_999),
        ],
    )
    def test_partial_update_restricted_field_ignored_success(
        self,
        restricted_field,
        new_value,
        auth_client,
        admin_user,
        company,
    ):
        original_value = getattr(company, restricted_field)

        response = auth_client(admin_user).patch(
            company_detail_url(company.id),
            {restricted_field: new_value},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company.refresh_from_db()
        if restricted_field == "created_by":
            assert company.created_by_id == original_value.id
        else:
            assert company.balance == Decimal("0.00")
            assert getattr(company, restricted_field) == original_value

    @pytest.mark.parametrize(
        ("field", "invalid_value"),
        [
            ("email", "not-an-email"),
            ("phone_number", "010000000001"),
            ("district", 999_999),
            ("name", "N" * 256),
        ],
    )
    def test_partial_update_invalid_field_fail(
        self,
        field,
        invalid_value,
        auth_client,
        admin_user,
        company,
    ):
        original_value = getattr(company, field)

        response = auth_client(admin_user).patch(
            company_detail_url(company.id),
            {field: invalid_value},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        company.refresh_from_db()
        if field == "district":
            assert company.district_id == original_value.id
        else:
            assert getattr(company, field) == original_value

    def test_full_update_company_success(
        self,
        auth_client,
        admin_user,
        company,
        company_payload_factory,
        geo_data,
    ):
        payload = company_payload_factory(name="Fully Updated Company")

        response = auth_client(admin_user).put(
            company_detail_url(company.id),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company.refresh_from_db()
        assert company.name == "Fully Updated Company"
        assert company.email == payload["email"]
        assert company.phone_number == payload["phone_number"]
        assert company.address == payload["address"]
        assert company.district_id == geo_data["district"].id
        assert company.updated_by_id == admin_user.id

    def test_full_update_missing_required_field_fail(
        self,
        auth_client,
        admin_user,
        company,
        company_payload_factory,
    ):
        payload = company_payload_factory()
        payload.pop("name")
        original_name = company.name

        response = auth_client(admin_user).put(
            company_detail_url(company.id),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        company.refresh_from_db()
        assert company.name == original_name

    def test_partial_update_unknown_company_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).patch(
            company_detail_url(999_999),
            {"name": "Missing"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
