from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.tests.api.v1.cash_request.helpers import (
    assert_cash_request_payload,
    cash_request_list_url,
    returned_ids,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCashRequestList:

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(cash_request_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_company_owner_scope_success(
        self,
        auth_client,
        company_owner,
        company,
        company_driver,
        driver_factory,
        other_company_branch,
        cash_request_factory,
    ):
        owned = cash_request_factory(company=company, driver=company_driver)
        other = cash_request_factory(
            company=other_company_branch.company,
            driver=driver_factory(branch=other_company_branch),
        )

        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        assert owned.id in returned_ids(response)
        assert other.id not in returned_ids(response)
        item = next(row for row in response.data["results"] if row["id"] == owned.id)
        assert_cash_request_payload(item, owned, company_owner)
        assert item["is_owner"] is True
        assert item["amount"] == "50.00"
        assert item["station_branch"] is None
        assert item["approved_by"] is None
        assert item["worker"] is None

    def test_list_branch_manager_is_owner_only_for_own_requests_success(
        self,
        auth_client,
        company_branch_manager,
        company,
        company_driver,
        cash_request_factory,
    ):
        owned = cash_request_factory(
            company=company,
            driver=company_driver,
            created_by=company_branch_manager,
        )
        other = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(company_branch_manager, company_id=company.id).get(
            cash_request_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        by_id = {row["id"]: row for row in response.data["results"]}
        assert owned.id in by_id
        assert other.id in by_id
        assert_cash_request_payload(by_id[owned.id], owned, company_branch_manager)
        assert by_id[owned.id]["is_owner"] is True
        assert_cash_request_payload(by_id[other.id], other, company_branch_manager)
        assert by_id[other.id]["is_owner"] is False

    def test_list_station_owner_only_station_linked_requests_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        company,
        company_driver,
        cash_request_factory,
    ):
        unlinked = cash_request_factory(company=company, driver=company_driver)
        linked = cash_request_factory(
            company=company,
            driver=company_driver,
            station=station,
            station_branch=branch,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("50.00"),
            approved_by=station_owner,
        )

        response = auth_client(station_owner, station_id=station.id).get(
            cash_request_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        assert linked.id in returned_ids(response)
        assert unlinked.id not in returned_ids(response)
        item = next(row for row in response.data["results"] if row["id"] == linked.id)
        assert_cash_request_payload(item, linked, station_owner)
        assert item["is_owner"] is False
        assert item["amount"] == "50.00"
        assert item["station_branch"]["id"] == branch.id
        assert item["station_branch"]["station"] == station.id
        assert item["approved_by"]["id"] == station_owner.id
        assert item["worker"] == item["approved_by"]

    def test_list_station_worker_without_driver_code_only_own_approved_success(
        self,
        auth_client,
        station_worker,
        station,
        branch,
        worker_factory,
        company,
        company_driver,
        cash_request_factory,
    ):
        other_worker = worker_factory()
        own_approved = cash_request_factory(
            company=company,
            driver=company_driver,
            station=station,
            station_branch=branch,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("50.00"),
            approved_by=station_worker,
        )
        other_approved = cash_request_factory(
            company=company,
            driver=company_driver,
            station=station,
            station_branch=branch,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("60.00"),
            approved_by=other_worker,
        )
        in_progress = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(station_worker, station_id=station.id).get(
            cash_request_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {own_approved.id}
        assert other_approved.id not in returned_ids(response)
        assert in_progress.id not in returned_ids(response)
        assert_cash_request_payload(
            response.data["results"][0], own_approved, station_worker
        )

    def test_list_station_worker_with_driver_code_in_progress_success(
        self,
        auth_client,
        station_worker,
        station,
        company,
        company_driver,
        cash_request_factory,
    ):
        in_progress = cash_request_factory(company=company, driver=company_driver)
        cash_request_factory(
            company=company,
            driver=company_driver,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("50.00"),
            approved_by=station_worker,
            station=station,
        )

        response = auth_client(station_worker, station_id=station.id).get(
            cash_request_list_url(),
            {"driver_code": company_driver.code},
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {in_progress.id}
        assert_cash_request_payload(
            response.data["results"][0], in_progress, station_worker
        )
        assert response.data["results"][0]["amount"] == "None"
        assert response.data["results"][0]["status"] == (
            CompanyCashRequest.Status.IN_PROGRESS
        )

    def test_list_dashboard_sees_all_success(
        self,
        auth_client,
        admin_user,
        company,
        company_driver,
        other_company_branch,
        driver_factory,
        cash_request_factory,
    ):
        first = cash_request_factory(company=company, driver=company_driver)
        second = cash_request_factory(
            company=other_company_branch.company,
            driver=driver_factory(branch=other_company_branch),
        )

        response = auth_client(admin_user).get(cash_request_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert {first.id, second.id}.issubset(returned_ids(response))
        item = next(row for row in response.data["results"] if row["id"] == first.id)
        assert_cash_request_payload(item, first, admin_user)
        assert item["is_owner"] is False
        assert item["amount"] == "50.00"

    def test_list_filter_status_success(
        self,
        auth_client,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        in_progress = cash_request_factory(company=company, driver=company_driver)
        approved = cash_request_factory(
            company=company,
            driver=company_driver,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("50.00"),
        )

        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_list_url(),
            {"status": CompanyCashRequest.Status.IN_PROGRESS},
        )

        assert response.status_code == status.HTTP_200_OK
        assert in_progress.id in returned_ids(response)
        assert approved.id not in returned_ids(response)

    def test_list_filter_company_branch_success(
        self,
        auth_client,
        company_owner,
        company,
        company_driver,
        second_company_branch,
        driver_factory,
        cash_request_factory,
    ):
        matching = cash_request_factory(company=company, driver=company_driver)
        other = cash_request_factory(
            company=company,
            driver=driver_factory(branch=second_company_branch),
        )

        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_list_url(),
            {"company_branch": company_driver.branch_id},
        )

        assert response.status_code == status.HTTP_200_OK
        assert matching.id in returned_ids(response)
        assert other.id not in returned_ids(response)

    def test_list_station_branch_manager_only_station_linked_requests_success(
        self,
        auth_client,
        branch_manager,
        station,
        branch,
        company,
        company_driver,
        cash_request_factory,
    ):
        unlinked = cash_request_factory(company=company, driver=company_driver)
        linked = cash_request_factory(
            company=company,
            driver=company_driver,
            station=station,
            station_branch=branch,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("50.00"),
            approved_by=branch_manager,
        )

        response = auth_client(branch_manager, station_id=station.id).get(
            cash_request_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        assert linked.id in returned_ids(response)
        assert unlinked.id not in returned_ids(response)
        item = next(row for row in response.data["results"] if row["id"] == linked.id)
        assert_cash_request_payload(item, linked, branch_manager)
        assert item["is_owner"] is False
        assert item["amount"] == "50.00"

    def test_list_filter_driver_and_approved_by_success(
        self,
        auth_client,
        company_owner,
        company,
        company_driver,
        driver_factory,
        station_worker,
        cash_request_factory,
    ):
        other_driver = driver_factory(name="Other Filter Driver")
        matching = cash_request_factory(
            company=company,
            driver=company_driver,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("50.00"),
            approved_by=station_worker,
        )
        other_driver_request = cash_request_factory(
            company=company,
            driver=other_driver,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("60.00"),
            approved_by=station_worker,
        )
        other_approver = cash_request_factory(
            company=company,
            driver=company_driver,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("70.00"),
        )

        by_driver = auth_client(company_owner, company_id=company.id).get(
            cash_request_list_url(),
            {"driver": company_driver.id},
        )
        by_approver = auth_client(company_owner, company_id=company.id).get(
            cash_request_list_url(),
            {"approved_by": station_worker.id},
        )

        assert by_driver.status_code == status.HTTP_200_OK
        assert matching.id in returned_ids(by_driver)
        assert other_approver.id in returned_ids(by_driver)
        assert other_driver_request.id not in returned_ids(by_driver)
        assert by_approver.status_code == status.HTTP_200_OK
        assert matching.id in returned_ids(by_approver)
        assert other_driver_request.id in returned_ids(by_approver)
        assert other_approver.id not in returned_ids(by_approver)

    def test_list_search_driver_name_success(
        self,
        auth_client,
        company_owner,
        company,
        driver_factory,
        cash_request_factory,
    ):
        matching_driver = driver_factory(name="Searchable Cash Driver")
        other_driver = driver_factory(name="Other Cash Driver")
        matching = cash_request_factory(company=company, driver=matching_driver)
        other = cash_request_factory(company=company, driver=other_driver)

        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_list_url(),
            {"search": "Searchable Cash Driver"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {matching.id}
        assert other.id not in returned_ids(response)
        assert_cash_request_payload(
            response.data["results"][0], matching, company_owner
        )

    def test_list_without_pagination_success(
        self,
        auth_client,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(company_owner, company_id=company.id).get(
            cash_request_list_url(),
            {"no_paginate": "true"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "count" not in response.data
        assert [item["id"] for item in response.data["results"]] == [cash_request.id]
        assert_cash_request_payload(
            response.data["results"][0], cash_request, company_owner
        )
