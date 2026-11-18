import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Driver
from apps.utilities.testing import assert_soft_deleted, listed_ids

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def driver_detail_url(driver_id):
    return reverse("drivers-detail", kwargs={"pk": driver_id})


class TestDriverDelete:

    def test_delete_without_authentication_fail(self, api_client, company_driver):
        response = api_client.delete(driver_detail_url(company_driver.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Driver.objects.filter(pk=company_driver.id).exists()

    def test_delete_driver_success(
        self,
        auth_client,
        company_owner,
        company,
        company_driver,
    ):
        response = auth_client(company_owner, company_id=company.id).delete(
            driver_detail_url(company_driver.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Driver.objects.filter(pk=company_driver.id).exists()

    def test_delete_outside_company_scope_fail(
        self,
        auth_client,
        company_owner,
        company,
        driver_factory,
        other_company_branch,
    ):
        other_driver = driver_factory(branch=other_company_branch)

        response = auth_client(company_owner, company_id=company.id).delete(
            driver_detail_url(other_driver.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Driver.objects.filter(pk=other_driver.id).exists()

    def test_delete_unknown_driver_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).delete(driver_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDriverSoftDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, company_owner, company, company_driver):
        self.client = auth_client(company_owner, company_id=company.id)
        self.driver = company_driver
        response = self.client.delete(driver_detail_url(company_driver.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(Driver, self.driver.id)

    def test_deleted_driver_hidden_from_list_success(self):
        response = self.client.get(reverse("drivers-list"))

        assert response.status_code == status.HTTP_200_OK
        assert self.driver.id not in listed_ids(response)

    def test_retrieve_deleted_driver_not_found_fail(self):
        response = self.client.get(driver_detail_url(self.driver.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_driver_not_found_fail(self):
        response = self.client.delete(driver_detail_url(self.driver.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_with_deleted_driver_license_number_fail(
        self, driver_payload_factory
    ):
        """The deleted driver still holds its unique license number."""
        self.client.raise_request_exception = False

        response = self.client.post(
            reverse("drivers-list"),
            driver_payload_factory(lincense_number=self.driver.lincense_number),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            Driver.all_objects.filter(
                lincense_number=self.driver.lincense_number
            ).count()
            == 1
        )
