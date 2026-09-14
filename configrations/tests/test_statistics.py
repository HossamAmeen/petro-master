from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import KhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.operation_model import CarOperation

pytestmark = [pytest.mark.api, pytest.mark.django_db]

# Pin "today" and every record's creation time to Cairo noon so the date
# filters don't depend on when the suite runs.
TODAY = date(2026, 3, 10)
OLD_DAY = TODAY - timedelta(days=10)


def at_noon(day):
    return datetime.combine(day, time(12), tzinfo=ZoneInfo("Africa/Cairo"))


def created_on(model, obj, day):
    model.objects.filter(pk=obj.pk).update(created=at_noon(day))


def statistics_url():
    return reverse("statistics")


class TestStatistics:

    def test_statistics_without_authentication_fail(self, api_client):
        response = api_client.get(statistics_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_statistics_as_non_admin_dashboard_user_fail(
        self, auth_client, finance_user
    ):
        response = auth_client(finance_user).get(statistics_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_statistics_counts_every_section_success(
        self,
        auth_client,
        admin_user,
        finance_user,
        company_owner,
        station_owner,
        company_factory,
        company_driver,
        car_operation_factory,
        cash_request_factory,
        company_transaction_factory,
        branch,
    ):
        company = company_owner.company
        company_factory(is_active=False)

        for day, request_status in [
            (TODAY, CompanyCashRequest.Status.APPROVED),
            (OLD_DAY, CompanyCashRequest.Status.APPROVED),
            (TODAY, CompanyCashRequest.Status.IN_PROGRESS),
        ]:
            cash_request = cash_request_factory(
                company=company, driver=company_driver, status=request_status
            )
            created_on(CompanyCashRequest, cash_request, day)

        for day, operation_status, profits in [
            (TODAY, CarOperation.OperationStatus.COMPLETED, "5.00"),
            (OLD_DAY, CarOperation.OperationStatus.COMPLETED, "7.00"),
            (TODAY, CarOperation.OperationStatus.PENDING, "100.00"),
        ]:
            operation = car_operation_factory(
                status=operation_status, profits=Decimal(profits)
            )
            created_on(CarOperation, operation, day)

        Approved = KhaznaTransaction.TransactionStatus.APPROVED
        company_transaction = company_transaction_factory(
            is_incoming=True, status=Approved
        )
        station_transaction = StationKhaznaTransaction.objects.create(
            station=branch.station,
            station_branch=branch,
            amount=Decimal("20.00"),
            is_incoming=False,
            status=Approved,
            reference_code="STATS-STATION",
            created_by=admin_user,
        )
        pending_transaction = KhaznaTransaction.objects.create(
            amount=Decimal("30.00"),
            is_incoming=False,
            reference_code="STATS-PENDING",
            created_by=admin_user,
        )
        for day, transaction in [
            (TODAY, company_transaction),
            (OLD_DAY, station_transaction),
            (TODAY, pending_transaction),
        ]:
            created_on(KhaznaTransaction, transaction, day)

        with patch("configrations.views.today", return_value=TODAY):
            response = auth_client(admin_user).get(statistics_url())

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data == {
            "users": {
                "total_users": 5,
                "admin_users": 1,
                "company_owners": 1,
                "station_owners": 1,
                "station_workers": 1,
            },
            "geo": {"total_countries": 1, "total_cities": 1, "total_districts": 1},
            "companies": {
                "total_companies": 2,
                "active_companies": 1,
                "total_cars": 1,
                "total_drivers": 1,
                "total_cash_requests": 2,
                "total_cash_requests_today": 1,
                "total_operations": 2,
                "total_today_operations": 1,
                "total_profit": Decimal("12.00"),
                "total_profit_today": Decimal("5.00"),
            },
            "company_branches": {"total_branches": 1},
            "stations": {"total_stations": 1},
            "station_branches": {"total_branches": 1},
            "transactions": {
                "total_transactions": 3,
                "total_today_transactions": 2,
                "total_incoming_today_transactions": 1,
                "total_incoming_transactions": 1,
                "total_outgoing_transactions": 2,
                "total_outgoing_today_transactions": 1,
                "total_approved_transactions": 2,
                "total_company_transactions": 1,
                "total_station_transactions": 1,
            },
            "services": {"total_services": 1},
        }
