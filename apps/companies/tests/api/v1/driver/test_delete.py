import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Driver


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def driver_detail_url(driver_id):
    return reverse("drivers-detail", kwargs={"pk": driver_id})


class TestDriverDelete:


    def test_delete_without_authentication_fail(self, api_client, company_driver):
        response = api_client.delete(driver_detail_url(company_driver.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Driver.objects.filter(pk=company_driver.id).exists()


    def test_delete_driver_success(self,
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


    def test_delete_outside_company_scope_fail(self,
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
