from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {item["id"] for item in response.data["results"]}


def test_list_without_authentication_fail(api_client):
    response = api_client.get(reverse("drivers-list"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_company_owner_scope_success(
    auth_client,
    company_owner,
    company,
    driver_factory,
    other_company_branch,
):
    owned_driver = driver_factory()
    other_driver = driver_factory(branch=other_company_branch)

    response = auth_client(company_owner, company_id=company.id).get(
        reverse("drivers-list")
    )

    assert response.status_code == status.HTTP_200_OK
    assert owned_driver.id in returned_ids(response)
    assert other_driver.id not in returned_ids(response)


def test_list_branch_manager_scope_success(
    auth_client,
    company_branch_manager,
    company,
    driver_factory,
    second_company_branch,
):
    managed_driver = driver_factory()
    unmanaged_driver = driver_factory(branch=second_company_branch)

    response = auth_client(company_branch_manager, company_id=company.id).get(
        reverse("drivers-list")
    )

    assert response.status_code == status.HTTP_200_OK
    assert managed_driver.id in returned_ids(response)
    assert unmanaged_driver.id not in returned_ids(response)


def test_list_dashboard_user_sees_all_drivers_success(
    auth_client,
    admin_user,
    driver_factory,
    other_company_branch,
):
    first_driver = driver_factory()
    second_driver = driver_factory(branch=other_company_branch)

    response = auth_client(admin_user).get(reverse("drivers-list"))

    assert response.status_code == status.HTTP_200_OK
    assert {first_driver.id, second_driver.id}.issubset(returned_ids(response))


def test_list_filter_branch_success(
    auth_client,
    company_owner,
    company,
    driver_factory,
    second_company_branch,
):
    matching_driver = driver_factory()
    non_matching_driver = driver_factory(branch=second_company_branch)

    response = auth_client(company_owner, company_id=company.id).get(
        reverse("drivers-list"),
        {"branch": matching_driver.branch_id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert matching_driver.id in returned_ids(response)
    assert non_matching_driver.id not in returned_ids(response)


def test_list_filter_city_success(
    auth_client,
    company_owner,
    company,
    geo_data,
    driver_factory,
    other_city_company_branch,
):
    matching_driver = driver_factory()
    non_matching_driver = driver_factory(branch=other_city_company_branch)

    response = auth_client(company_owner, company_id=company.id).get(
        reverse("drivers-list"),
        {"city": geo_data["city"].id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert matching_driver.id in returned_ids(response)
    assert non_matching_driver.id not in returned_ids(response)


def test_list_filter_company_success(
    auth_client,
    admin_user,
    company,
    driver_factory,
    other_company_branch,
):
    matching_driver = driver_factory()
    non_matching_driver = driver_factory(branch=other_company_branch)

    response = auth_client(admin_user).get(
        reverse("drivers-list"),
        {"company": company.id},
    )

    assert response.status_code == status.HTTP_200_OK
    assert matching_driver.id in returned_ids(response)
    assert non_matching_driver.id not in returned_ids(response)


@pytest.mark.parametrize(
    ("days_until_expiry", "query_parameter", "query_offset_days", "should_match"),
    [
        (10, "lincense_expiration_date__to", 30, True),
        (200, "lincense_expiration_date__to", 30, False),
        (200, "lincense_expiration_date__from", 90, True),
        (10, "lincense_expiration_date__from", 90, False),
    ],
)
def test_list_filter_license_expiration_success(
    days_until_expiry,
    query_parameter,
    query_offset_days,
    should_match,
    auth_client,
    company_owner,
    company,
    driver_factory,
):
    today = timezone.localdate()
    driver = driver_factory(
        lincense_expiration_date=today + timedelta(days=days_until_expiry)
    )

    response = auth_client(company_owner, company_id=company.id).get(
        reverse("drivers-list"),
        {query_parameter: (today + timedelta(days=query_offset_days)).isoformat()},
    )

    assert response.status_code == status.HTTP_200_OK
    if should_match:
        assert driver.id in returned_ids(response)
    else:
        assert driver.id not in returned_ids(response)


def test_list_search_success(
    auth_client,
    company_owner,
    company,
    driver_factory,
):
    matching_driver = driver_factory(name="Searchable Driver")
    non_matching_driver = driver_factory(name="Other Driver")

    response = auth_client(company_owner, company_id=company.id).get(
        reverse("drivers-list"),
        {"search": "Searchable Driver"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert returned_ids(response) == {matching_driver.id}
    assert non_matching_driver.id not in returned_ids(response)


def test_list_without_pagination_success(
    auth_client,
    company_owner,
    company,
    company_driver,
):
    response = auth_client(company_owner, company_id=company.id).get(
        reverse("drivers-list"),
        {"no_paginate": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "count" not in response.data
    assert [item["id"] for item in response.data["results"]] == [company_driver.id]
    assert response.data["results"][0]["name"] == company_driver.name
    assert response.data["results"][0]["company_name"] == company.name
