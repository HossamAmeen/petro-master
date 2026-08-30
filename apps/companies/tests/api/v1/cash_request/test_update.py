from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.tests.api.v1.cash_request.helpers import (
    cash_request_detail_url,
    set_balance,
)
from apps.notifications.models import Notification
from apps.users.models import CompanyUser, StationOwner


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCashRequestUpdate:


    def test_partial_update_without_authentication_fail(self,
        api_client, company, company_driver, cash_request_factory
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = api_client.patch(
            cash_request_detail_url(cash_request.id),
            {"otp": cash_request.otp},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    @pytest.mark.parametrize(
        "role_fixture",
        ["company_owner", "company_branch_manager", "admin_user", "station_owner"],
    )
    def test_partial_update_forbidden_role_fail(self,
        role_fixture,
        request,
        auth_client,
        company,
        station,
        company_driver,
        cash_request_factory,
    ):
        user = request.getfixturevalue(role_fixture)
        cash_request = cash_request_factory(company=company, driver=company_driver)
        client_kwargs = {}
        if role_fixture in {"company_owner", "company_branch_manager"}:
            client_kwargs["company_id"] = company.id
        if role_fixture == "station_owner":
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).patch(
            cash_request_detail_url(cash_request.id),
            {"otp": cash_request.otp},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.IN_PROGRESS


    def test_partial_update_approve_as_station_worker_success(self,
        auth_client,
        station_worker,
        station,
        branch,
        branch_manager,
        station_owner,
        company_owner,
        company_branch_manager,
        company,
        company_branch,
        company_driver,
        cash_request_factory,
    ):
        company_branch.cash_request_fees = Decimal("10.00")
        company_branch.save(update_fields=["cash_request_fees"])
        branch.cash_request_fees = Decimal("5.00")
        branch.save(update_fields=["cash_request_fees"])
        set_balance(branch, "200.00")
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            amount=Decimal("100.00"),
            company_cost=Decimal("110.00"),
        )

        response = auth_client(station_worker, station_id=station.id).patch(
            cash_request_detail_url(cash_request.id),
            {"otp": cash_request.otp},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {"message": "تم تأكيد طلبك"}
        cash_request.refresh_from_db()
        branch.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.APPROVED
        assert cash_request.station_id == station.id
        assert cash_request.station_branch_id == branch.id
        assert cash_request.approved_by_id == station_worker.id
        assert cash_request.station_cost == Decimal("105.00")
        assert cash_request.company_cost == Decimal("110.00")
        assert cash_request.amount == Decimal("100.00")
        assert branch.balance == Decimal("95.00")

        company_txn = CompanyKhaznaTransaction.objects.get()
        assert company_txn.company_id == company.id
        assert company_txn.company_branch_id == company_branch.id
        assert company_txn.amount == Decimal("110.00")
        assert company_txn.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED
        assert company_txn.is_internal is False
        assert company_txn.for_what == CompanyKhaznaTransaction.ForWhat.DRIVER
        assert company_txn.created_by_id == station_worker.id
        assert company_driver.name in company_txn.description
        assert "110.00" in company_txn.description

        station_txn = StationKhaznaTransaction.objects.get()
        assert station_txn.station_id == station.id
        assert station_txn.station_branch_id == branch.id
        assert station_txn.amount == Decimal("105.00")
        assert station_txn.status == StationKhaznaTransaction.TransactionStatus.APPROVED
        assert station_txn.is_internal is False
        assert station_txn.created_by_id == station_worker.id
        assert company_driver.name in station_txn.description
        assert "105.00" in station_txn.description

        money_user_ids = set(
            Notification.objects.filter(
                type=Notification.NotificationType.MONEY
            ).values_list("user_id", flat=True)
        )
        assert company_branch_manager.id in money_user_ids
        assert station_worker.id in money_user_ids
        assert branch_manager.id in money_user_ids
        assert money_user_ids & set(
            CompanyUser.objects.filter(company_id=company.id).values_list("pk", flat=True)
        )
        assert money_user_ids & set(
            StationOwner.objects.filter(station_id=station.id).values_list("pk", flat=True)
        )
        company_message = (
            f"تم تسليم طلب نقدي بقيمة {cash_request.company_cost:.2f} "
            f"للسائق {company_driver.name}"
        )
        station_message = (
            f"تم تسليم طلب نقدي بقيمة {cash_request.station_cost:.2f} "
            f"للسائق {company_driver.name}"
        )
        titles = set(
            Notification.objects.filter(
                type=Notification.NotificationType.MONEY
            ).values_list("title", flat=True)
        )
        assert company_message in titles
        assert station_message in titles


    def test_partial_update_insufficient_station_balance_goes_negative_success(self,
        auth_client,
        station_worker,
        station,
        branch,
        station_owner,
        company_owner,
        company,
        company_driver,
        cash_request_factory,
    ):
        set_balance(branch, "10.00")
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            amount=Decimal("50.00"),
            company_cost=Decimal("50.00"),
        )

        response = auth_client(station_worker, station_id=station.id).patch(
            cash_request_detail_url(cash_request.id),
            {"otp": cash_request.otp},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        cash_request.refresh_from_db()
        branch.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.APPROVED
        assert cash_request.station_cost == Decimal("50.00")
        assert branch.balance == Decimal("-40.00")


    def test_partial_update_wrong_otp_fail(self,
        auth_client,
        station_worker,
        station,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(station_worker, station_id=station.id).patch(
            cash_request_detail_url(cash_request.id),
            {"otp": "000000"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.IN_PROGRESS
        assert cash_request.approved_by_id is None
        assert StationKhaznaTransaction.objects.count() == 0
        assert CompanyKhaznaTransaction.objects.count() == 0


    def test_partial_update_already_approved_fail(self,
        auth_client,
        station_worker,
        station,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(
            company=company,
            driver=company_driver,
            status=CompanyCashRequest.Status.APPROVED,
            station_cost=Decimal("50.00"),
            approved_by=station_worker,
            station=station,
        )

        response = auth_client(station_worker, station_id=station.id).patch(
            cash_request_detail_url(cash_request.id),
            {"otp": cash_request.otp},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CompanyKhaznaTransaction.objects.count() == 0


    def test_partial_update_missing_otp_fail(self,
        auth_client,
        station_worker,
        station,
        company,
        company_driver,
        cash_request_factory,
    ):
        cash_request = cash_request_factory(company=company, driver=company_driver)

        response = auth_client(station_worker, station_id=station.id).patch(
            cash_request_detail_url(cash_request.id),
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.IN_PROGRESS


    def test_partial_update_unknown_request_fail(self,
        auth_client, station_worker, station
    ):
        response = auth_client(station_worker, station_id=station.id).patch(
            cash_request_detail_url(999_999),
            {"otp": "123456"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "الطلب غير موجود"
