from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def driver_detail_url(driver_id):
    return reverse("drivers-detail", kwargs={"pk": driver_id})


def test_retrieve_without_authentication_fail(api_client, company_driver):
    response = api_client.get(driver_detail_url(company_driver.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_owned_driver_success(
    auth_client,
    company_owner,
    company,
    company_driver,
):
    response = auth_client(company_owner, company_id=company.id).get(
        driver_detail_url(company_driver.id)
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == company_driver.id
    assert response.data["name"] == company_driver.name
    assert response.data["code"] == company_driver.code
    assert response.data["branch"]["id"] == company_driver.branch_id
    assert response.data["company_name"] == company.name
    assert response.data["is_license_expiring_soon"] is False


def test_retrieve_outside_company_scope_fail(
    auth_client,
    company_owner,
    company,
    driver_factory,
    other_company_branch,
):
    other_driver = driver_factory(branch=other_company_branch)

    response = auth_client(company_owner, company_id=company.id).get(
        driver_detail_url(other_driver.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_unknown_driver_fail(auth_client, admin_user):
    response = auth_client(admin_user).get(driver_detail_url(999_999))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    ("days_until_expiry", "expected"),
    [
        (0, True),
        (30, True),
        (31, False),
    ],
)
def test_retrieve_license_expiring_soon_success(
    days_until_expiry,
    expected,
    auth_client,
    company_owner,
    company,
    driver_factory,
):
    driver = driver_factory(
        lincense_expiration_date=timezone.localdate()
        + timedelta(days=days_until_expiry)
    )

    response = auth_client(company_owner, company_id=company.id).get(
        driver_detail_url(driver.id)
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_license_expiring_soon"] is expected
