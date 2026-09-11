from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Car
from apps.stations.models.service_models import Service

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def home_url():
    return reverse("company-home")


class TestCompanyHome:

    def test_home_without_authentication_fail(self, api_client):
        response = api_client.get(home_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        [
            "admin_user",
            "finance_user",
            "customer_support_user",
            "station_owner",
            "station_worker",
        ],
    )
    def test_home_forbidden_role_fail(
        self, role_fixture, request, auth_client, company, station
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {"company_id": company.id}
        if role_fixture in {"station_owner", "station_worker"}:
            client_kwargs = {"station_id": station.id}

        response = auth_client(user, **client_kwargs).get(home_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_home_owner_without_company_claim_fail(self, auth_client, company_owner):
        response = auth_client(company_owner).get(home_url())

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Company not found"

    def test_home_owner_unknown_company_claim_fail(self, auth_client, company_owner):
        response = auth_client(company_owner, company_id=999_999).get(home_url())

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["message"] == "Company not found"

    def test_home_post_not_allowed_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).post(home_url())

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_home_owner_empty_company_success(
        self, auth_client, company_owner, company
    ):
        response = auth_client(company_owner, company_id=company.id).get(home_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == company.name
        assert response.data["total_cars_count"] == 0
        assert response.data["diesel_cars_count"] == 0
        assert response.data["gasoline_cars_count"] == 0
        assert response.data["total_drivers_count"] == 0
        assert response.data["total_drivers_with_lincense_expiration_date"] == 0
        assert response.data["total_drivers_with_lincense_expiration_date_30_days"] == 0
        assert response.data["total_branches_count"] == 0
        assert response.data["total_branch_count"] == 0
        assert response.data["balance"] == 0
        assert response.data["cars_balance"] == 0
        assert response.data["branches_balance"] == 0
        assert response.data["cash_requests_balance"] == 0
        assert response.data["total_balance"] == 0
        assert response.data["car_operations"] == []
        assert response.data["company_transactions"] == []
        assert list(response.data["branches"]) == []

    def test_home_owner_aggregates_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        second_company_branch,
        car_factory,
        driver_factory,
        cash_request_factory,
        other_company_branch,
    ):
        company.balance = Decimal("100.00")
        company.save(update_fields=["balance"])
        company_branch.balance = Decimal("40.00")
        company_branch.save(update_fields=["balance"])
        second_company_branch.balance = Decimal("60.00")
        second_company_branch.save(update_fields=["balance"])
        other_company_branch.balance = Decimal("999.00")
        other_company_branch.save(update_fields=["balance"])

        car_factory(balance=Decimal("25.00"), fuel_type=Car.FuelType.GASOLINE)
        car_factory(
            branch=second_company_branch,
            balance=Decimal("15.00"),
            fuel_type=Car.FuelType.DIESEL,
        )
        car_factory(fuel_type=Car.FuelType.ELECTRIC, balance=Decimal("5.00"))
        car_factory(
            branch=other_company_branch,
            fuel_type=Car.FuelType.GASOLINE,
            balance=Decimal("500.00"),
        )

        valid_driver = driver_factory()
        driver_factory(branch=second_company_branch)
        driver_factory(branch=other_company_branch)

        cash_request_factory(
            company=company, driver=valid_driver, amount=Decimal("12.00")
        )
        cash_request_factory(
            company=company,
            driver=valid_driver,
            amount=Decimal("8.00"),
            status=CompanyCashRequest.Status.APPROVED,
        )
        cash_request_factory(
            company=other_company_branch.company,
            driver=driver_factory(branch=other_company_branch),
            amount=Decimal("77.00"),
        )

        response = auth_client(company_owner, company_id=company.id).get(home_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == company.name
        assert response.data["total_cars_count"] == 3
        assert response.data["diesel_cars_count"] == 1
        assert response.data["gasoline_cars_count"] == 1
        assert response.data["total_drivers_count"] == 2
        assert response.data["total_branches_count"] == 2
        assert response.data["total_branch_count"] == 2
        assert response.data["balance"] == Decimal("100.00")
        assert response.data["cars_balance"] == Decimal("45.00")
        assert response.data["branches_balance"] == Decimal("100.00")
        assert response.data["cash_requests_balance"] == Decimal("12.00")
        assert response.data["total_balance"] == Decimal("257.00")
        assert set(response.data["branches"]) == {
            company_branch.id,
            second_company_branch.id,
        }

    def test_home_manager_scoped_to_assigned_branch_success(
        self,
        auth_client,
        company_owner,
        company_branch_manager,
        company,
        company_branch,
        second_company_branch,
        car_factory,
        driver_factory,
        cash_request_factory,
    ):
        company.balance = Decimal("100.00")
        company.save(update_fields=["balance"])
        company_branch.balance = Decimal("40.00")
        company_branch.save(update_fields=["balance"])
        second_company_branch.balance = Decimal("60.00")
        second_company_branch.save(update_fields=["balance"])

        car_factory(balance=Decimal("25.00"), fuel_type=Car.FuelType.GASOLINE)
        car_factory(
            branch=second_company_branch,
            balance=Decimal("15.00"),
            fuel_type=Car.FuelType.DIESEL,
        )
        managed_driver = driver_factory()
        unmanaged_driver = driver_factory(branch=second_company_branch)
        cash_request_factory(
            company=company, driver=managed_driver, amount=Decimal("12.00")
        )
        cash_request_factory(
            company=company, driver=unmanaged_driver, amount=Decimal("30.00")
        )

        owner_response = auth_client(company_owner, company_id=company.id).get(
            home_url()
        )
        manager_response = auth_client(
            company_branch_manager, company_id=company.id
        ).get(home_url())

        assert owner_response.status_code == status.HTTP_200_OK
        assert manager_response.status_code == status.HTTP_200_OK
        assert owner_response.data["total_branches_count"] == 2
        assert manager_response.data["total_branches_count"] == 1
        assert manager_response.data["total_cars_count"] == 1
        assert manager_response.data["gasoline_cars_count"] == 1
        assert manager_response.data["diesel_cars_count"] == 0
        assert manager_response.data["total_drivers_count"] == 1
        assert manager_response.data["balance"] == Decimal("40.00")
        assert manager_response.data["cars_balance"] == Decimal("25.00")
        assert manager_response.data["branches_balance"] == Decimal("40.00")
        assert manager_response.data["cash_requests_balance"] == Decimal("12.00")
        assert manager_response.data["total_balance"] == Decimal("77.00")
        assert set(manager_response.data["branches"]) == {company_branch.id}
        assert second_company_branch.id not in set(manager_response.data["branches"])

    def test_home_license_expiration_counts_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        driver_factory,
    ):
        today = timezone.localdate()
        driver_factory(lincense_expiration_date=today + timedelta(days=10))
        driver_factory(lincense_expiration_date=today - timedelta(days=10))
        driver_factory(lincense_expiration_date=today - timedelta(days=40))

        response = auth_client(company_owner, company_id=company.id).get(home_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_drivers_count"] == 3
        assert response.data["total_drivers_with_lincense_expiration_date"] == 2
        assert response.data["total_drivers_with_lincense_expiration_date_30_days"] == 1

    def test_home_recent_operations_limited_and_scoped_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        second_company_branch,
        other_company_branch,
        company_driver,
        driver_factory,
        car_factory,
        car_operation_factory,
    ):
        owned_car = car_factory()
        unmanaged_car = car_factory(branch=second_company_branch)
        other_car = car_factory(branch=other_company_branch)
        other_driver = driver_factory(branch=other_company_branch)

        older = car_operation_factory(
            car=owned_car,
            driver=company_driver,
            unit=Service.ServiceUnit.LITRE,
        )
        middle = car_operation_factory(
            car=owned_car,
            driver=company_driver,
            unit=Service.ServiceUnit.LITRE,
        )
        third = car_operation_factory(
            car=unmanaged_car,
            driver=driver_factory(branch=second_company_branch),
            unit=Service.ServiceUnit.LITRE,
        )
        newest = car_operation_factory(
            car=owned_car,
            driver=company_driver,
            unit=Service.ServiceUnit.LITRE,
        )
        other_operation = car_operation_factory(
            car=other_car,
            driver=other_driver,
            unit=Service.ServiceUnit.LITRE,
        )

        response = auth_client(company_owner, company_id=company.id).get(home_url())

        assert response.status_code == status.HTTP_200_OK
        operation_ids = [item["id"] for item in response.data["car_operations"]]
        assert operation_ids == [newest.id, third.id, middle.id]
        assert older.id not in operation_ids
        assert other_operation.id not in operation_ids
        assert response.data["car_operations"][0]["car"]["id"] == owned_car.id
        assert response.data["car_operations"][0]["unit"] == "لتر"

    def test_home_manager_operations_exclude_unassigned_branch_success(
        self,
        auth_client,
        company_branch_manager,
        company,
        company_branch,
        second_company_branch,
        company_driver,
        driver_factory,
        car_factory,
        car_operation_factory,
    ):
        managed_op = car_operation_factory(
            car=car_factory(),
            driver=company_driver,
        )
        unmanaged_op = car_operation_factory(
            car=car_factory(branch=second_company_branch),
            driver=driver_factory(branch=second_company_branch),
        )

        response = auth_client(company_branch_manager, company_id=company.id).get(
            home_url()
        )

        assert response.status_code == status.HTTP_200_OK
        operation_ids = {item["id"] for item in response.data["car_operations"]}
        assert managed_op.id in operation_ids
        assert unmanaged_op.id not in operation_ids

    def test_home_recent_transactions_limited_and_scoped_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        second_company_branch,
        other_company_branch,
        company_transaction_factory,
    ):
        older = company_transaction_factory()
        company_transaction_factory()
        newest = company_transaction_factory(company_branch=second_company_branch)
        company_transaction_factory()
        other_txn = company_transaction_factory(
            company=other_company_branch.company,
            company_branch=other_company_branch,
            reference_code="OTHER00001",
        )
        unbranched = company_transaction_factory(
            company_branch=None, reference_code="NOBR00001"
        )

        response = auth_client(company_owner, company_id=company.id).get(home_url())

        assert response.status_code == status.HTTP_200_OK
        transaction_ids = [item["id"] for item in response.data["company_transactions"]]
        assert len(transaction_ids) == 3
        assert older.id not in transaction_ids
        assert other_txn.id not in transaction_ids
        assert unbranched.id not in transaction_ids
        assert newest.id in transaction_ids

    def test_home_rejected_cash_request_not_counted_success(
        self,
        auth_client,
        company_owner,
        company,
        company_branch,
        driver_factory,
        cash_request_factory,
    ):
        driver = driver_factory()
        cash_request_factory(
            company=company,
            driver=driver,
            amount=Decimal("20.00"),
            status=CompanyCashRequest.Status.REJECTED,
        )

        response = auth_client(company_owner, company_id=company.id).get(home_url())

        assert response.status_code == status.HTTP_200_OK
        assert response.data["cash_requests_balance"] == 0
