from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import CompanyBranch


pytestmark = [pytest.mark.api, pytest.mark.django_db]


REQUIRED_FIELDS = ["name", "company"]


def test_create_without_authentication_fail(
    api_client, company_branch_payload_factory
):
    response = api_client.post(
        reverse("company-branches-list"),
        company_branch_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert CompanyBranch.objects.count() == 0


@pytest.mark.parametrize(
    "role_fixture",
    ["company_owner", "company_branch_manager", "station_worker"],
)
def test_create_forbidden_role_fail(
    role_fixture,
    request,
    auth_client,
    company,
    station,
    company_branch_payload_factory,
):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture in {"company_owner", "company_branch_manager"}:
        client_kwargs["company_id"] = company.id
    if role_fixture == "station_worker":
        client_kwargs["station_id"] = station.id

    existing_ids = set(CompanyBranch.objects.values_list("id", flat=True))

    response = auth_client(user, **client_kwargs).post(
        reverse("company-branches-list"),
        company_branch_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert set(CompanyBranch.objects.values_list("id", flat=True)) == existing_ids


@pytest.mark.parametrize("role_fixture", ["admin_user", "finance_user"])
def test_create_branch_success(
    role_fixture,
    request,
    auth_client,
    company,
    geo_data,
    company_branch_payload_factory,
):
    user = request.getfixturevalue(role_fixture)
    payload = company_branch_payload_factory()

    response = auth_client(user).post(
        reverse("company-branches-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyBranch.objects.get(name=payload["name"])
    assert created.company_id == company.id
    assert created.district_id == geo_data["district"].id
    assert created.email == payload["email"]
    assert created.phone_number == payload["phone_number"]
    assert created.address == payload["address"]
    assert created.balance == Decimal("0.00")
    assert created.created_by_id == user.id


def test_create_without_optional_fields_success(
    auth_client, admin_user, company, company_branch_payload_factory
):
    payload = company_branch_payload_factory()
    for field in [
        "email",
        "phone_number",
        "address",
        "district",
        "fees",
        "other_service_fees",
        "cash_request_fees",
    ]:
        payload.pop(field)

    response = auth_client(admin_user).post(
        reverse("company-branches-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyBranch.objects.get(name=payload["name"])
    assert created.company_id == company.id
    assert created.district_id is None
    assert created.email is None
    assert created.fees == Decimal("0.00")
    assert created.created_by_id == admin_user.id


def test_create_with_fees_success(
    auth_client, admin_user, company_branch_payload_factory
):
    payload = company_branch_payload_factory(
        fees="5.50",
        other_service_fees="2.25",
        cash_request_fees="1.00",
    )

    response = auth_client(admin_user).post(
        reverse("company-branches-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyBranch.objects.get(name=payload["name"])
    assert created.fees == Decimal("5.50")
    assert created.other_service_fees == Decimal("2.25")
    assert created.cash_request_fees == Decimal("1.00")


def test_create_submitted_balance_ignored_success(
    auth_client, admin_user, company_branch_payload_factory
):
    payload = company_branch_payload_factory()
    payload["balance"] = "999.00"

    response = auth_client(admin_user).post(
        reverse("company-branches-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyBranch.objects.get(name=payload["name"])
    assert created.balance == Decimal("0.00")


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_create_missing_required_field_fail(
    missing_field,
    auth_client,
    admin_user,
    company_branch_payload_factory,
):
    payload = company_branch_payload_factory()
    payload.pop(missing_field)
    existing_ids = set(CompanyBranch.objects.values_list("id", flat=True))

    response = auth_client(admin_user).post(
        reverse("company-branches-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert set(CompanyBranch.objects.values_list("id", flat=True)) == existing_ids


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("email", "not-an-email"),
        ("phone_number", "010000000001"),
        ("district", 999_999),
        ("company", 999_999),
        ("name", "N" * 256),
        ("fees", "1000.00"),
    ],
)
def test_create_invalid_field_fail(
    field,
    invalid_value,
    auth_client,
    admin_user,
    company_branch_payload_factory,
):
    payload = company_branch_payload_factory(**{field: invalid_value})
    existing_ids = set(CompanyBranch.objects.values_list("id", flat=True))

    response = auth_client(admin_user).post(
        reverse("company-branches-list"),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert set(CompanyBranch.objects.values_list("id", flat=True)) == existing_ids
