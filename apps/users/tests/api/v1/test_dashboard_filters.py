import pytest
from rest_framework import status

from apps.users.tests.helpers import (
    company_branch_managers_list_url,
    company_owners_list_url,
    returned_ids,
    workers_list_url,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyOwnerFilters:
    @pytest.mark.parametrize("param", ["company", "company_id"])
    def test_filter_by_company_success(
        self,
        param,
        auth_client,
        admin_user,
        company,
        company_owner,
        other_company_owner,
    ):
        response = auth_client(admin_user).get(
            company_owners_list_url(**{param: company.id})
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert company_owner.id in ids
        assert other_company_owner.id not in ids


class TestCompanyBranchManagerFilters:
    @pytest.mark.parametrize("param", ["company", "company_id"])
    def test_filter_by_company_success(
        self,
        param,
        auth_client,
        admin_user,
        company,
        company_branch_manager,
        other_company_branch_manager,
    ):
        response = auth_client(admin_user).get(
            company_branch_managers_list_url(**{param: company.id})
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert company_branch_manager.id in ids
        assert other_company_branch_manager.id not in ids


class TestWorkerFilters:
    @pytest.mark.parametrize("param", ["branch", "station_branch"])
    def test_filter_by_branch_success(
        self,
        param,
        auth_client,
        admin_user,
        branch,
        station_worker,
        other_station_worker,
    ):
        response = auth_client(admin_user).get(workers_list_url(**{param: branch.id}))

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station_worker.id in ids
        assert other_station_worker.id not in ids

    def test_filter_by_station_success(
        self, auth_client, admin_user, station, station_worker, other_station_worker
    ):
        response = auth_client(admin_user).get(workers_list_url(station=station.id))

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station_worker.id in ids
        assert other_station_worker.id not in ids
