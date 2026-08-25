from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def car_detail_url(car_id):
    return reverse("cars-detail", kwargs={"pk": car_id})


def test_partial_update_without_authentication_fail(api_client, company_car):
    response = api_client.patch(
        car_detail_url(company_car.id),
        {"brand": "Updated"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_partial_update_company_car_success(
    auth_client,
    company_owner,
    company,
    company_car,
):
    response = auth_client(company_owner, company_id=company.id).patch(
        car_detail_url(company_car.id),
        {"brand": "Updated"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    company_car.refresh_from_db()
    assert company_car.brand == "Updated"
    assert company_car.updated_by_id == company_owner.id


@pytest.mark.parametrize(
    ("restricted_field", "new_value"),
    [
        ("balance", "999.00"),
        ("is_blocked_balance_update", True),
        ("last_meter", 99_999),
        ("code", "RESTRICT01"),
    ],
)
def test_partial_update_company_restricted_field_ignored_success(
    restricted_field,
    new_value,
    auth_client,
    company_owner,
    company,
    company_car,
):
    original_value = getattr(company_car, restricted_field)

    response = auth_client(company_owner, company_id=company.id).patch(
        car_detail_url(company_car.id),
        {restricted_field: new_value},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    company_car.refresh_from_db()
    assert getattr(company_car, restricted_field) == original_value


def test_partial_update_dashboard_balance_success(
    auth_client,
    admin_user,
    company_car,
):
    response = auth_client(admin_user).patch(
        car_detail_url(company_car.id),
        {"balance": "125.50"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    company_car.refresh_from_db()
    assert company_car.balance == Decimal("125.50")


def test_partial_update_outside_company_scope_fail(
    auth_client,
    company_owner,
    company,
    car_factory,
    other_company_branch,
):
    other_car = car_factory(branch=other_company_branch)

    response = auth_client(company_owner, company_id=company.id).patch(
        car_detail_url(other_car.id),
        {"brand": "Forbidden"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    other_car.refresh_from_db()
    assert other_car.brand != "Forbidden"


def test_partial_update_permitted_fuel_above_capacity_fail(
    auth_client,
    company_owner,
    company,
    company_car,
):
    response = auth_client(company_owner, company_id=company.id).patch(
        car_detail_url(company_car.id),
        {"permitted_fuel_amount": company_car.tank_capacity + 1},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    company_car.refresh_from_db()
    assert company_car.permitted_fuel_amount <= company_car.tank_capacity


def test_full_update_car_success(
    auth_client,
    company_owner,
    company,
    company_car,
    car_code_factory,
    car_payload_factory,
):
    car_code = car_code_factory(code=company_car.code)
    payload = car_payload_factory(
        car_code=car_code,
        code=company_car.code,
        branch=company_car.branch_id,
        brand="Fully Updated",
    )

    response = auth_client(company_owner, company_id=company.id).put(
        car_detail_url(company_car.id),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    company_car.refresh_from_db()
    assert company_car.brand == "Fully Updated"
    assert company_car.updated_by_id == company_owner.id


def test_full_update_missing_required_field_fail(
    auth_client,
    company_owner,
    company,
    company_car,
    car_code_factory,
    car_payload_factory,
):
    car_code = car_code_factory(code=company_car.code)
    payload = car_payload_factory(
        car_code=car_code,
        code=company_car.code,
        branch=company_car.branch_id,
    )
    payload.pop("brand")

    response = auth_client(company_owner, company_id=company.id).put(
        car_detail_url(company_car.id),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
