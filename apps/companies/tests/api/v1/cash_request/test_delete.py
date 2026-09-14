from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.tests.api.v1.cash_request.helpers import (
    cash_request_detail_url,
    set_balance,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCashRequestDelete:

    def test_delete_without_authentication_fail(
        self, api_client, company, company_driver, cash_request_factory
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = api_client.delete(cash_request_detail_url(cash_request.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CompanyCashRequest.objects.filter(pk=cash_request.id).exists()

    @pytest.mark.parametrize("role_fixture", ["station_worker", "station_owner"])
    def test_delete_station_role_fail(
        self,
        role_fixture,
        request,
        auth_client,
        station,
        company,
        company_driver,
        cash_request_factory,
    ):
        user = request.getfixturevalue(role_fixture)
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(user, station_id=station.id).delete(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.IN_PROGRESS

    def test_delete_in_progress_as_company_owner_refunds_company_success(
        self,
        auth_client,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        set_balance(company, "90.00")
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            amount=Decimal("100.00"),
            company_cost=Decimal("110.00"),
            created_by=company_owner,
        )

        response = auth_client(company_owner, company_id=company.id).delete(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.data is None or response.data == ""
        cash_request.refresh_from_db()
        company.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.REJECTED
        assert cash_request.company_cost == Decimal("110.00")
        assert cash_request.amount == Decimal("100.00")
        assert cash_request.driver_id == company_driver.id
        assert company.balance == Decimal("200.00")

    def test_delete_in_progress_as_creator_manager_refunds_branch_success(
        self,
        auth_client,
        company_branch_manager,
        company,
        company_branch,
        company_driver,
        cash_request_factory,
    ):
        set_balance(company_branch, "90.00")
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            amount=Decimal("100.00"),
            company_cost=Decimal("110.00"),
            created_by=company_branch_manager,
        )

        response = auth_client(company_branch_manager, company_id=company.id).delete(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        cash_request.refresh_from_db()
        company_branch.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.REJECTED
        assert company_branch.balance == Decimal("200.00")

    def test_delete_manager_created_request_as_owner_refunds_company_success(
        self,
        auth_client,
        company_owner,
        company_branch_manager,
        company,
        company_branch,
        company_driver,
        cash_request_factory,
    ):
        set_balance(company, "90.00")
        set_balance(company_branch, "90.00")
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            amount=Decimal("100.00"),
            company_cost=Decimal("110.00"),
            created_by=company_branch_manager,
        )

        response = auth_client(company_owner, company_id=company.id).delete(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        cash_request.refresh_from_db()
        company.refresh_from_db()
        company_branch.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.REJECTED
        assert company.balance == Decimal("200.00")
        assert company_branch.balance == Decimal("90.00")

    def test_delete_as_dashboard_refunds_branch_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_driver,
        cash_request_factory,
    ):
        set_balance(company, "90.00")
        set_balance(company_branch, "90.00")
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            amount=Decimal("100.00"),
            company_cost=Decimal("110.00"),
            created_by=admin_user,
        )

        response = auth_client(admin_user, company_id=company.id).delete(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        cash_request.refresh_from_db()
        company.refresh_from_db()
        company_branch.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.REJECTED
        assert company.balance == Decimal("90.00")
        assert company_branch.balance == Decimal("200.00")

    def test_delete_request_created_by_someone_else_as_manager_fail(
        self,
        auth_client,
        company_branch_manager,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            created_by=company_owner,
        )

        response = auth_client(company_branch_manager, company_id=company.id).delete(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "permission_denied"
        assert company_owner.name in str(response.data["message"])
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.IN_PROGRESS

    @pytest.mark.parametrize(
        "request_status",
        [
            CompanyCashRequest.Status.APPROVED,
            CompanyCashRequest.Status.REJECTED,
        ],
    )
    def test_delete_non_in_progress_fail(
        self,
        request_status,
        auth_client,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        set_balance(company, "100.00")
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            status=request_status,
            station_cost=Decimal("50.00"),
            created_by=company_owner,
        )

        response = auth_client(company_owner, company_id=company.id).delete(
            cash_request_detail_url(cash_request.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert request_status in str(response.data["message"])
        cash_request.refresh_from_db()
        company.refresh_from_db()
        assert cash_request.status == request_status
        assert company.balance == Decimal("100.00")

    def test_delete_other_company_as_owner_fail(
        self,
        auth_client,
        company_owner,
        company,
        other_company_branch,
        driver_factory,
        cash_request_factory,
    ):
        other = cash_request_factory(
            company=other_company_branch.company,
            driver=driver_factory(branch=other_company_branch),
        )

        response = auth_client(company_owner, company_id=company.id).delete(
            cash_request_detail_url(other.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        other.refresh_from_db()
        assert other.status == CompanyCashRequest.Status.IN_PROGRESS

    def test_delete_unknown_request_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).delete(
            cash_request_detail_url(999_999)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_put_not_allowed_fail(
        self, auth_client, company_owner, company, company_driver, cash_request_factory
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(company_owner, company_id=company.id).put(
            cash_request_detail_url(cash_request.id),
            {"otp": cash_request.otp},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
