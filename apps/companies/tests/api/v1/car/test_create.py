import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Car


pytestmark = [pytest.mark.api, pytest.mark.django_db]


REQUIRED_FIELDS = [
    "code",
    "plate_color",
    "color",
    "model_year",
    "brand",
    "is_with_odometer",
    "tank_capacity",
    "permitted_fuel_amount",
    "number_of_fuelings_per_day",
    "number_of_washes_per_month",
    "branch",
]


def test_create_without_authentication_fail(api_client, car_payload_factory):
    response = api_client.post(
        reverse("cars-list"),
        car_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Car.objects.count() == 0


def test_create_car_success(
    auth_client,
    company_owner,
    company,
    company_branch,
    car_payload_factory,
):
    payload = car_payload_factory()

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("cars-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created_car = Car.objects.get(pk=response.data["id"])
    assert created_car.code == payload["code"]
    assert created_car.branch == company_branch
    assert created_car.created_by_id == company_owner.id


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_create_missing_required_field_fail(
    missing_field,
    auth_client,
    company_owner,
    company,
    car_payload_factory,
):
    payload = car_payload_factory()
    payload.pop(missing_field)

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("cars-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Car.objects.count() == 0


def test_create_unknown_car_code_fail(
    auth_client,
    company_owner,
    company,
    car_payload_factory,
):
    payload = car_payload_factory(code="UNKNOWN001")

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("cars-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Car.objects.count() == 0


def test_create_duplicate_car_code_fail(
    auth_client,
    company_owner,
    company,
    car_factory,
    car_code_factory,
    car_payload_factory,
):
    car_code = car_code_factory()
    car_factory(code=car_code.code)
    payload = car_payload_factory(car_code=car_code)

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("cars-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Car.objects.filter(code=car_code.code).count() == 1


def test_create_permitted_fuel_above_capacity_fail(
    auth_client,
    company_owner,
    company,
    car_payload_factory,
):
    payload = car_payload_factory(
        tank_capacity=50,
        permitted_fuel_amount=51,
    )

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("cars-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Car.objects.count() == 0


def test_create_same_primary_and_backup_service_fail(
    auth_client,
    company_owner,
    company,
    service,
    car_payload_factory,
):
    payload = car_payload_factory(backup_service=service.id)

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("cars-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Car.objects.count() == 0


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("plate_color", "#INVALID"),
        ("fuel_type", "invalid-fuel"),
    ],
)
def test_create_invalid_choice_fail(
    field,
    invalid_value,
    auth_client,
    company_owner,
    company,
    car_payload_factory,
):
    payload = car_payload_factory(**{field: invalid_value})

    response = auth_client(company_owner, company_id=company.id).post(
        reverse("cars-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Car.objects.count() == 0
