import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Driver


pytestmark = [pytest.mark.api, pytest.mark.django_db]


REQUIRED_FIELDS = [
    "name",
    "phone_number",
    "lincense_number",
    "lincense_expiration_date",
    "branch",
]


def test_create_without_authentication_fail(api_client, driver_payload_factory):
    response = api_client.post(
        reverse("drivers-list"),
        driver_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Driver.objects.count() == 0


def test_create_driver_success(
    auth_client,
    company_owner,
    company,
    company_branch,
    driver_payload_factory,
):
    payload = driver_payload_factory()

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("drivers-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created_driver = Driver.objects.get(pk=response.data["id"])
    assert created_driver.name == payload["name"]
    assert created_driver.phone_number == payload["phone_number"]
    assert created_driver.lincense_number == payload["lincense_number"]
    assert created_driver.branch == company_branch
    assert created_driver.created_by_id == company_owner.id
    assert created_driver.code


def test_create_as_branch_manager_success(
    auth_client,
    company_branch_manager,
    company,
    company_branch,
    driver_payload_factory,
):
    payload = driver_payload_factory()

    response = auth_client(company_branch_manager, company_id=company.id).post(
        reverse("drivers-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created_driver = Driver.objects.get(pk=response.data["id"])
    assert created_driver.branch == company_branch
    assert created_driver.created_by_id == company_branch_manager.id


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_create_missing_required_field_fail(
    missing_field,
    auth_client,
    company_owner,
    company,
    driver_payload_factory,
):
    payload = driver_payload_factory()
    payload.pop(missing_field)

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("drivers-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Driver.objects.count() == 0


def test_create_submitted_code_ignored_success(
    auth_client,
    company_owner,
    company,
    driver_payload_factory,
):
    payload = driver_payload_factory(code="CLIENTCODE")

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("drivers-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created_driver = Driver.objects.get(pk=response.data["id"])
    assert created_driver.code != "CLIENTCODE"


def test_create_duplicate_license_number_fail(
    auth_client,
    company_owner,
    company,
    driver_factory,
    driver_payload_factory,
):
    existing_driver = driver_factory()
    payload = driver_payload_factory(lincense_number=existing_driver.lincense_number)

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("drivers-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Driver.objects.filter(
        lincense_number=existing_driver.lincense_number
    ).count() == 1


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("phone_number", "010000000001"),
        ("lincense_number", "X" * 21),
        ("lincense_expiration_date", "26-08-2026"),
        ("branch", 999_999),
    ],
)
def test_create_invalid_field_fail(
    field,
    invalid_value,
    auth_client,
    company_owner,
    company,
    driver_payload_factory,
):
    payload = driver_payload_factory(**{field: invalid_value})

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("drivers-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Driver.objects.count() == 0
