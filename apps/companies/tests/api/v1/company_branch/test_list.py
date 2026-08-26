import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {item["id"] for item in response.data["results"]}


class TestCompanyBranchList:


    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(reverse("company-branches-list"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    @pytest.mark.parametrize(
        "role_fixture",
        ["station_owner", "branch_manager", "station_worker"],
    )
    def test_list_station_role_fail(self,
        role_fixture, request, auth_client, station, company_branch
    ):
        user = request.getfixturevalue(role_fixture)

        response = auth_client(user, station_id=station.id).get(
            reverse("company-branches-list")
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


    @pytest.mark.parametrize("role_fixture", ["admin_user", "finance_user"])
    def test_list_dashboard_sees_all_branches_success(self,
        role_fixture,
        request,
        auth_client,
        company_branch,
        other_company_branch,
    ):
        user = request.getfixturevalue(role_fixture)

        response = auth_client(user).get(reverse("company-branches-list"))

        assert response.status_code == status.HTTP_200_OK
        assert {company_branch.id, other_company_branch.id}.issubset(returned_ids(response))


    def test_list_company_owner_scope_success(self,
        auth_client,
        company_owner,
        company,
        company_branch,
        second_company_branch,
        other_company_branch,
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            reverse("company-branches-list")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert {company_branch.id, second_company_branch.id}.issubset(ids)
        assert other_company_branch.id not in ids


    def test_list_branch_manager_scope_success(self,
        auth_client,
        company_branch_manager,
        company,
        company_branch,
        second_company_branch,
        other_company_branch,
    ):
        response = auth_client(company_branch_manager, company_id=company.id).get(
            reverse("company-branches-list")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert company_branch.id in ids
        assert second_company_branch.id not in ids
        assert other_company_branch.id not in ids


    def test_list_company_owner_without_company_claim_is_empty_success(self,
        auth_client, company_owner, company_branch
    ):
        response = auth_client(company_owner).get(reverse("company-branches-list"))

        assert response.status_code == status.HTTP_200_OK
        assert company_branch.id not in returned_ids(response)


    def test_list_includes_annotated_counts_success(self,
        auth_client,
        admin_user,
        company_branch,
        second_company_branch,
        company_car,
        company_driver,
        company_branch_manager,
    ):
        response = auth_client(admin_user).get(reverse("company-branches-list"))

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        assert listed[company_branch.id]["cars_count"] == 1
        assert listed[company_branch.id]["drivers_count"] == 1
        assert listed[company_branch.id]["managers_count"] == 1
        assert listed[second_company_branch.id]["cars_count"] == 0
        assert listed[second_company_branch.id]["drivers_count"] == 0
        assert listed[second_company_branch.id]["managers_count"] == 0


    def test_list_ordered_by_newest_first_success(self,
        auth_client, admin_user, company_branch_factory
    ):
        older = company_branch_factory()
        newer = company_branch_factory()

        response = auth_client(admin_user).get(reverse("company-branches-list"))

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert ids.index(newer.id) < ids.index(older.id)


    def test_list_filter_company_success(self,
        auth_client,
        admin_user,
        company,
        company_branch,
        other_company_branch,
    ):
        response = auth_client(admin_user).get(
            reverse("company-branches-list"),
            {"company": company.id},
        )

        assert response.status_code == status.HTTP_200_OK
        assert company_branch.id in returned_ids(response)
        assert other_company_branch.id not in returned_ids(response)


    def test_list_filter_city_success(self,
        auth_client,
        admin_user,
        geo_data,
        company_branch,
        other_city_company_branch,
    ):
        response = auth_client(admin_user).get(
            reverse("company-branches-list"),
            {"city": geo_data["city"].id},
        )

        assert response.status_code == status.HTTP_200_OK
        assert company_branch.id in returned_ids(response)
        assert other_city_company_branch.id not in returned_ids(response)


    def test_list_filter_unknown_city_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(
            reverse("company-branches-list"),
            {"city": 999_999},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


    def test_list_owner_filter_cannot_see_other_company_success(self,
        auth_client,
        company_owner,
        company,
        other_company,
        company_branch,
        other_company_branch,
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            reverse("company-branches-list"),
            {"company": other_company.id},
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == set()


    @pytest.mark.parametrize("no_paginate", ["true", "TRUE", "True"])
    def test_list_without_pagination_success(self,
        no_paginate, auth_client, admin_user, company_branch
    ):
        response = auth_client(admin_user).get(
            reverse("company-branches-list"),
            {"no_paginate": no_paginate},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "count" not in response.data
        assert response.data["results"] == [
            {"id": company_branch.id, "name": company_branch.name}
        ]
