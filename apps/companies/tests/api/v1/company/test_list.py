import pytest
from django.urls import reverse
from rest_framework import status

from apps.geo.models import City, District

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {item["id"] for item in response.data["results"]}


class TestCompanyList:

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(reverse("companies-list"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        [
            "admin_user",
            "finance_user",
            "company_owner",
            "company_branch_manager",
            "station_owner",
            "station_worker",
        ],
    )
    def test_list_authenticated_role_success(
        self,
        role_fixture,
        request,
        auth_client,
        company,
        other_company,
        station,
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture in {"company_owner", "company_branch_manager"}:
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker"}:
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).get(reverse("companies-list"))

        assert response.status_code == status.HTTP_200_OK
        assert {company.id, other_company.id}.issubset(returned_ids(response))

    def test_list_includes_annotated_counts_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        second_company_branch,
        company_car,
        company_driver,
        company_branch_manager,
        other_company,
        other_company_branch,
        car_factory,
        driver_factory,
    ):
        car_factory(branch=other_company_branch)
        driver_factory(branch=other_company_branch)

        response = auth_client(admin_user).get(reverse("companies-list"))

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        assert listed[company.id]["total_branches"] == 2
        assert listed[company.id]["total_cars"] == 1
        assert listed[company.id]["total_drivers"] == 1
        assert listed[company.id]["total_managers"] == 1
        assert listed[other_company.id]["total_branches"] == 1
        assert listed[other_company.id]["total_cars"] == 1
        assert listed[other_company.id]["total_drivers"] == 1
        assert listed[other_company.id]["total_managers"] == 0

    def test_list_ordered_by_newest_first_success(
        self, auth_client, admin_user, company_factory
    ):
        older = company_factory()
        newer = company_factory()

        response = auth_client(admin_user).get(reverse("companies-list"))

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert ids.index(newer.id) < ids.index(older.id)

    def test_list_filter_district_success(
        self,
        auth_client,
        admin_user,
        geo_data,
        company_factory,
    ):
        matching = company_factory()
        other_district = District.objects.create(name="Zamalek", city=geo_data["city"])
        non_matching = company_factory(district=other_district)

        response = auth_client(admin_user).get(
            reverse("companies-list"),
            {"district": matching.district_id},
        )

        assert response.status_code == status.HTTP_200_OK
        assert matching.id in returned_ids(response)
        assert non_matching.id not in returned_ids(response)

    def test_list_filter_city_success(
        self,
        auth_client,
        admin_user,
        geo_data,
        company_factory,
    ):
        matching = company_factory()
        other_city = City.objects.create(name="Giza", country=geo_data["country"])
        other_district = District.objects.create(name="Dokki", city=other_city)
        non_matching = company_factory(district=other_district)

        response = auth_client(admin_user).get(
            reverse("companies-list"),
            {"city": geo_data["city"].id},
        )

        assert response.status_code == status.HTTP_200_OK
        assert matching.id in returned_ids(response)
        assert non_matching.id not in returned_ids(response)

    def test_list_filter_unknown_district_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(
            reverse("companies-list"),
            {"district": 999_999},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_search_by_name_success(
        self, auth_client, admin_user, company_factory
    ):
        matching = company_factory(name="Searchable Company")
        non_matching = company_factory(name="Other Company")

        response = auth_client(admin_user).get(
            reverse("companies-list"),
            {"search": "Searchable Company"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {matching.id}
        assert non_matching.id not in returned_ids(response)

    def test_list_search_by_phone_number_success(
        self, auth_client, admin_user, company_factory
    ):
        matching = company_factory(phone_number="01011111111")
        non_matching = company_factory(phone_number="01022222222")

        response = auth_client(admin_user).get(
            reverse("companies-list"),
            {"search": "01011111111"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {matching.id}
        assert non_matching.id not in returned_ids(response)

    @pytest.mark.parametrize("no_paginate", ["true", "TRUE", "True"])
    def test_list_without_pagination_success(
        self, no_paginate, auth_client, admin_user, company
    ):
        response = auth_client(admin_user).get(
            reverse("companies-list"),
            {"no_paginate": no_paginate},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "count" not in response.data
        assert response.data["results"] == [{"id": company.id, "name": company.name}]

    def test_list_with_pagination_includes_counts_success(
        self, auth_client, admin_user, company
    ):
        response = auth_client(admin_user).get(reverse("companies-list"))

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert response.data["results"][0]["id"] == company.id
        assert "total_branches" in response.data["results"][0]
        assert "district" in response.data["results"][0]
