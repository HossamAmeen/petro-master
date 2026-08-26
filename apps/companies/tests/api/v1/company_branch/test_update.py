from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.geo.models import District


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def branch_detail_url(branch_id):
    return reverse("company-branches-detail", kwargs={"pk": branch_id})


class TestCompanyBranchUpdate:


    def test_partial_update_without_authentication_fail(self, api_client, company_branch):
        response = api_client.patch(
            branch_detail_url(company_branch.id),
            {"name": "Updated Branch"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_partial_update_branch_success(self, auth_client, admin_user, company_branch):
        response = auth_client(admin_user).patch(
            branch_detail_url(company_branch.id),
            {"name": "Updated Branch"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch.refresh_from_db()
        assert company_branch.name == "Updated Branch"
        assert company_branch.updated_by_id == admin_user.id


    def test_partial_update_fees_success(self, auth_client, admin_user, company_branch):
        response = auth_client(admin_user).patch(
            branch_detail_url(company_branch.id),
            {"fees": "7.50", "cash_request_fees": "3.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch.refresh_from_db()
        assert company_branch.fees == Decimal("7.50")
        assert company_branch.cash_request_fees == Decimal("3.00")


    def test_partial_update_owned_branch_as_company_owner_success(self,
        auth_client, company_owner, company, company_branch
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            branch_detail_url(company_branch.id),
            {"name": "Owner Updated Branch"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch.refresh_from_db()
        assert company_branch.name == "Owner Updated Branch"
        assert company_branch.updated_by_id == company_owner.id


    def test_partial_update_other_company_branch_as_owner_fail(self,
        auth_client, company_owner, company, other_company_branch
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            branch_detail_url(other_company_branch.id),
            {"name": "Forbidden"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        other_company_branch.refresh_from_db()
        assert other_company_branch.name != "Forbidden"


    def test_partial_update_unmanaged_branch_as_branch_manager_fail(self,
        auth_client, company_branch_manager, company, second_company_branch
    ):
        response = auth_client(company_branch_manager, company_id=company.id).patch(
            branch_detail_url(second_company_branch.id),
            {"name": "Forbidden"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        second_company_branch.refresh_from_db()
        assert second_company_branch.name != "Forbidden"


    def test_partial_update_district_ignored_success(self,
        auth_client, admin_user, company_branch, geo_data
    ):
        other_district = District.objects.create(name="Zamalek", city=geo_data["city"])
        original_district_id = company_branch.district_id

        response = auth_client(admin_user).patch(
            branch_detail_url(company_branch.id),
            {"district": other_district.id},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch.refresh_from_db()
        assert company_branch.district_id == original_district_id


    def test_partial_update_balance_success(self, auth_client, admin_user, company_branch):
        response = auth_client(admin_user).patch(
            branch_detail_url(company_branch.id),
            {"balance": "125.50"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch.refresh_from_db()
        assert company_branch.balance == Decimal("125.50")


    @pytest.mark.parametrize(
        ("field", "invalid_value"),
        [
            ("email", "not-an-email"),
            ("phone_number", "010000000001"),
            ("name", "N" * 256),
            ("fees", "1000.00"),
            ("company", 999_999),
        ],
    )
    def test_partial_update_invalid_field_fail(self,
        field,
        invalid_value,
        auth_client,
        admin_user,
        company_branch,
    ):
        original_value = getattr(company_branch, field)

        response = auth_client(admin_user).patch(
            branch_detail_url(company_branch.id),
            {field: invalid_value},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        company_branch.refresh_from_db()
        if field == "company":
            assert company_branch.company_id == original_value.id
        else:
            assert getattr(company_branch, field) == original_value


    def test_full_update_branch_success(self,
        auth_client, admin_user, company, company_branch
    ):
        payload = {
            "name": "Fully Updated Branch",
            "company": company.id,
            "created_by": admin_user.id,
        }

        response = auth_client(admin_user).put(
            branch_detail_url(company_branch.id),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch.refresh_from_db()
        assert company_branch.name == "Fully Updated Branch"
        assert company_branch.updated_by_id == admin_user.id


    def test_full_update_missing_required_field_fail(self,
        auth_client, admin_user, company, company_branch
    ):
        original_name = company_branch.name

        response = auth_client(admin_user).put(
            branch_detail_url(company_branch.id),
            {"company": company.id, "created_by": admin_user.id},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        company_branch.refresh_from_db()
        assert company_branch.name == original_name


    def test_partial_update_unknown_branch_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).patch(
            branch_detail_url(999_999),
            {"name": "Missing"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
