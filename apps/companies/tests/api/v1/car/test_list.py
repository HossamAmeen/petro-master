import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Car

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {item["id"] for item in response.data["results"]}


class TestCarList:

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(reverse("cars-list"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_company_owner_scope_success(
        self,
        auth_client,
        company_owner,
        company,
        car_factory,
        other_company_branch,
    ):
        owned_car = car_factory()
        other_car = car_factory(branch=other_company_branch)

        response = auth_client(company_owner, company_id=company.id).get(
            reverse("cars-list")
        )

        assert response.status_code == status.HTTP_200_OK
        assert owned_car.id in returned_ids(response)
        assert other_car.id not in returned_ids(response)

    def test_list_branch_manager_scope_success(
        self,
        auth_client,
        company_branch_manager,
        company,
        car_factory,
        other_company_branch,
    ):
        managed_car = car_factory()
        unmanaged_car = car_factory(branch=other_company_branch)

        response = auth_client(company_branch_manager, company_id=company.id).get(
            reverse("cars-list")
        )

        assert response.status_code == status.HTTP_200_OK
        assert managed_car.id in returned_ids(response)
        assert unmanaged_car.id not in returned_ids(response)

    def test_list_dashboard_user_sees_all_cars_success(
        self,
        auth_client,
        admin_user,
        car_factory,
        other_company_branch,
    ):
        first_car = car_factory()
        second_car = car_factory(branch=other_company_branch)

        response = auth_client(admin_user).get(reverse("cars-list"))

        assert response.status_code == status.HTTP_200_OK
        assert {first_car.id, second_car.id}.issubset(returned_ids(response))

    @pytest.mark.parametrize(
        ("query_parameter", "query_value"),
        [
            ("fuel_type", Car.FuelType.GASOLINE),
            ("is_with_odometer", "true"),
        ],
    )
    def test_list_filter_success(
        self,
        query_parameter,
        query_value,
        auth_client,
        company_owner,
        company,
        car_factory,
    ):
        matching_car = car_factory(
            fuel_type=Car.FuelType.GASOLINE,
            is_with_odometer=True,
        )
        non_matching_car = car_factory(
            fuel_type=Car.FuelType.DIESEL,
            is_with_odometer=False,
        )

        response = auth_client(company_owner, company_id=company.id).get(
            reverse("cars-list"),
            {query_parameter: query_value},
        )

        assert response.status_code == status.HTTP_200_OK
        assert matching_car.id in returned_ids(response)
        assert non_matching_car.id not in returned_ids(response)

    def test_list_search_success(
        self,
        auth_client,
        company_owner,
        company,
        car_factory,
    ):
        matching_car = car_factory(code="SEARCH0001")
        non_matching_car = car_factory(code="OTHER00001")

        response = auth_client(company_owner, company_id=company.id).get(
            reverse("cars-list"),
            {"search": "SEARCH0001"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {matching_car.id}
        assert non_matching_car.id not in returned_ids(response)

    def test_list_without_pagination_success(
        self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            reverse("cars-list"),
            {"no_paginate": "true"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == [
            {
                "id": company_car.id,
                "code": company_car.code,
                "plate_number": company_car.plate_number,
                "plate_character": company_car.plate_character,
                "plate_color": company_car.plate_color,
            }
        ]
