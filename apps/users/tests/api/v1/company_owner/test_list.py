import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import company_owners_list_url, returned_ids, user_ref


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_list_without_authentication_fail(api_client):
    response = api_client.get(company_owners_list_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "role_fixture",
    ["company_owner", "company_branch_manager", "station_owner", "station_worker"],
)
def test_list_non_dashboard_fail(role_fixture, request, auth_client, company, station):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture in {"company_owner", "company_branch_manager"}:
        client_kwargs["company_id"] = company.id
    if role_fixture in {"station_owner", "station_worker"}:
        client_kwargs["station_id"] = station.id

    response = auth_client(user, **client_kwargs).get(company_owners_list_url())

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "role_fixture",
    ["admin_user", "finance_user", "customer_support_user"],
)
def test_list_dashboard_success(
    role_fixture,
    request,
    auth_client,
    company_owner,
    other_company_owner,
    company_branch_manager,
):
    user = request.getfixturevalue(role_fixture)

    response = auth_client(user).get(company_owners_list_url(no_paginate="true"))

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert {company_owner.id, other_company_owner.id}.issubset(ids)
    assert company_branch_manager.id not in ids


def test_list_includes_payload_fields_success(
    auth_client, admin_user, company_owner, company
):
    response = auth_client(admin_user).get(company_owners_list_url(no_paginate="true"))

    assert response.status_code == status.HTTP_200_OK
    listed = {item["id"]: item for item in response.data["results"]}
    row = listed[company_owner.id]
    assert row["name"] == company_owner.name
    assert row["email"] == company_owner.email
    assert row["phone_number"] == company_owner.phone_number
    assert row["role"] == User.UserRoles.CompanyOwner
    assert row["company_id"] == company.id
    assert row["created_by"] == user_ref(admin_user)


def test_list_search_by_phone_success(
    auth_client, admin_user, company_owner, other_company_owner
):
    response = auth_client(admin_user).get(
        company_owners_list_url(
            search=company_owner.phone_number, no_paginate="true"
        )
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert company_owner.id in ids
    assert other_company_owner.id not in ids
