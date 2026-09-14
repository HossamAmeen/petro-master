import pytest
from rest_framework import status

from apps.users.models import CompanyBranchManager
from apps.users.tests.helpers import company_branch_managers_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyBranchManagerUpdate:

    def test_update_without_authentication_fail(
        self, api_client, company_branch_manager
    ):
        response = api_client.patch(
            company_branch_managers_detail_url(company_branch_manager.id),
            {"name": "Hacker"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_as_station_worker_fail(
        self, auth_client, station_worker, station, company_branch_manager
    ):
        response = auth_client(station_worker, station_id=station.id).patch(
            company_branch_managers_detail_url(company_branch_manager.id),
            {"name": "Nope"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_name_as_company_owner_success(
        self, auth_client, company_owner, company, company_branch_manager
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            company_branch_managers_detail_url(company_branch_manager.id),
            {"name": "Updated Manager"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch_manager.refresh_from_db()
        assert company_branch_manager.name == "Updated Manager"
        assert company_branch_manager.company_id == company.id

    def test_update_adds_branch_assignments_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch_manager,
        second_company_branch,
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            company_branch_managers_detail_url(company_branch_manager.id),
            {"company_branches": [second_company_branch.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assigned = set(
            CompanyBranchManager.objects.filter(
                user=company_branch_manager
            ).values_list("company_branch_id", flat=True)
        )
        assert second_company_branch.id in assigned

    def test_update_password_success(
        self, auth_client, company_owner, company, company_branch_manager
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            company_branch_managers_detail_url(company_branch_manager.id),
            {"password": "manager-pass-1"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        company_branch_manager.refresh_from_db()
        assert company_branch_manager.check_password("manager-pass-1")

    def test_update_as_dashboard_raises_keyerror_fail(
        self, auth_client, admin_user, company_branch_manager
    ):
        """Documents actual (buggy) behavior: for dashboard users
        `CompanyBranchManagerSerializer.update` reads `validated_data["company_id"]`,
        but `company_id` is a read-only field, so it is never present and every
        dashboard PATCH crashes with an unhandled `KeyError` (HTTP 500)."""
        with pytest.raises(KeyError, match="company_id"):
            auth_client(admin_user).patch(
                company_branch_managers_detail_url(company_branch_manager.id),
                {"name": "Dashboard Rename"},
                format="json",
            )

        company_branch_manager.refresh_from_db()
        assert company_branch_manager.name != "Dashboard Rename"

    def test_update_other_company_manager_as_branch_manager_success(
        self,
        auth_client,
        company,
        company_branch_manager,
        other_company_branch_manager,
        other_company,
    ):
        """Documents actual (buggy) behavior: `get_queryset` only scopes company
        owners, so a company branch manager can edit branch managers of any
        company."""
        response = auth_client(company_branch_manager, company_id=company.id).patch(
            company_branch_managers_detail_url(other_company_branch_manager.id),
            {"name": "Renamed Across Companies"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        other_company_branch_manager.refresh_from_db()
        assert other_company_branch_manager.name == "Renamed Across Companies"
        assert other_company_branch_manager.company_id == other_company.id
