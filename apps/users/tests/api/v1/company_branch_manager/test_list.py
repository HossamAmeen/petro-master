import pytest
from rest_framework import status

from apps.users.tests.helpers import (
    company_branch_managers_list_url,
    returned_ids,
    user_ref,
)


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_list_without_authentication_fail(api_client):
    response = api_client.get(company_branch_managers_list_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("role_fixture", ["station_owner", "station_worker", "driver_user"])
def test_list_station_or_driver_fail(role_fixture, request, auth_client, station):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture in {"station_owner", "station_worker"}:
        client_kwargs["station_id"] = station.id

    response = auth_client(user, **client_kwargs).get(
        company_branch_managers_list_url()
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_as_company_owner_is_company_scoped_success(
    auth_client,
    company_owner,
    company,
    company_branch_manager,
    other_company_branch_manager,
):
    response = auth_client(company_owner, company_id=company.id).get(
        company_branch_managers_list_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert company_branch_manager.id in ids
    assert other_company_branch_manager.id not in ids


def test_list_as_dashboard_sees_all_success(
    auth_client,
    admin_user,
    company_branch_manager,
    other_company_branch_manager,
):
    response = auth_client(admin_user).get(
        company_branch_managers_list_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert {company_branch_manager.id, other_company_branch_manager.id}.issubset(ids)


def test_list_filter_by_branch_success(
    auth_client,
    admin_user,
    company_branch,
    company_branch_manager,
    other_company_branch_manager,
):
    response = auth_client(admin_user).get(
        company_branch_managers_list_url(
            branch=company_branch.id, no_paginate="true"
        )
    )

    assert response.status_code == status.HTTP_200_OK
    ids = returned_ids(response)
    assert company_branch_manager.id in ids
    assert other_company_branch_manager.id not in ids


def test_list_includes_payload_fields_success(
    auth_client, admin_user, company_branch_manager, company
):
    response = auth_client(admin_user).get(
        company_branch_managers_list_url(no_paginate="true")
    )

    assert response.status_code == status.HTTP_200_OK
    listed = {item["id"]: item for item in response.data["results"]}
    row = listed[company_branch_manager.id]
    assert row["name"] == company_branch_manager.name
    assert row["company_id"] == company.id
    assert row["created_by"] == user_ref(admin_user)
    assert "company_branches" not in row
