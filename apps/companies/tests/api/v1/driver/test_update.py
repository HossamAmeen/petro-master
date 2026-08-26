from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def driver_detail_url(driver_id):
    return reverse("drivers-detail", kwargs={"pk": driver_id})


class TestDriverUpdate:


    def test_partial_update_without_authentication_fail(self, api_client, company_driver):
        response = api_client.patch(
            driver_detail_url(company_driver.id),
            {"name": "Updated Driver"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_partial_update_company_driver_success(self,
        auth_client,
        company_owner,
        company,
        company_driver,
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            driver_detail_url(company_driver.id),
            {"name": "Updated Driver"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        company_driver.refresh_from_db()
        assert company_driver.name == "Updated Driver"
        assert company_driver.updated_by_id == company_owner.id


    def test_partial_update_code_ignored_success(self,
        auth_client,
        company_owner,
        company,
        company_driver,
    ):
        original_code = company_driver.code

        response = auth_client(company_owner, company_id=company.id).patch(
            driver_detail_url(company_driver.id),
            {"code": "RESTRICT01"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_driver.refresh_from_db()
        assert company_driver.code == original_code


    def test_partial_update_outside_company_scope_fail(self,
        auth_client,
        company_owner,
        company,
        driver_factory,
        other_company_branch,
    ):
        other_driver = driver_factory(branch=other_company_branch)

        response = auth_client(company_owner, company_id=company.id).patch(
            driver_detail_url(other_driver.id),
            {"name": "Forbidden"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        other_driver.refresh_from_db()
        assert other_driver.name != "Forbidden"


    def test_partial_update_duplicate_license_number_fail(self,
        auth_client,
        company_owner,
        company,
        driver_factory,
        company_driver,
    ):
        other_driver = driver_factory()

        response = auth_client(company_owner, company_id=company.id).patch(
            driver_detail_url(company_driver.id),
            {"lincense_number": other_driver.lincense_number},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        company_driver.refresh_from_db()
        assert company_driver.lincense_number != other_driver.lincense_number


    def test_full_update_driver_success(self,
        auth_client,
        company_owner,
        company,
        company_driver,
        driver_payload_factory,
    ):
        payload = driver_payload_factory(
            name="Fully Updated Driver",
            branch=company_driver.branch_id,
            lincense_number=company_driver.lincense_number,
            lincense_expiration_date=(
                timezone.localdate() + timedelta(days=400)
            ).isoformat(),
        )

        response = auth_client(company_owner, company_id=company.id).put(
            driver_detail_url(company_driver.id),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_driver.refresh_from_db()
        assert company_driver.name == "Fully Updated Driver"
        assert company_driver.phone_number == payload["phone_number"]
        assert company_driver.updated_by_id == company_owner.id


    def test_full_update_missing_required_field_fail(self,
        auth_client,
        company_owner,
        company,
        company_driver,
        driver_payload_factory,
    ):
        payload = driver_payload_factory(
            branch=company_driver.branch_id,
            lincense_number=company_driver.lincense_number,
        )
        payload.pop("name")

        response = auth_client(company_owner, company_id=company.id).put(
            driver_detail_url(company_driver.id),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
