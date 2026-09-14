"""A station worker fuels a company car, from verify-driver to the reports.

Each test follows the Given-When-Then template; the shared arrangement (a
funded car, a signed-in worker, fee percentages) lives in the ``setup`` fixture.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_models import Car
from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import operation_list_url
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification
from apps.stations.tests.helpers import (
    gas_url,
    notification_user_ids,
    operations_url,
    reports_url,
)

from .helpers import (
    company_home_url,
    fresh_balance,
    fuel,
    pump,
    read_meter,
    sign_in,
    start_fueling,
    start_pump,
    verify,
)

pytestmark = [pytest.mark.django_db, pytest.mark.feature]


def ids(items):
    return [item["id"] for item in items]


class TestFueling:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        fees,
        fuelable_car,
        company_driver,
        company,
        company_branch,
        company_owner,
        company_branch_manager,
        station,
        branch,
        station_owner,
        station_worker,
    ):
        self.car = fuelable_car
        self.driver = company_driver
        self.company = company
        self.company_branch = company_branch
        self.company_owner = company_owner
        self.company_manager = company_branch_manager
        self.station_branch = branch
        self.station_owner = station_owner
        self.worker_user = station_worker
        set_balance(branch, "500.00")
        self.worker = sign_in("station", station_worker)

    def fund(self, balance_source, amount="1000.00"):
        """Point the car at one balance holder and fund only that holder."""
        self.car.balance_source = balance_source
        self.car.save(update_fields=["balance_source"])
        holder = self.car.balance_holder
        set_balance(holder, amount)
        return holder

    def holders(self):
        return [self.car, self.company_branch, self.company]

    @pytest.mark.parametrize("balance_source", Car.BalanceSource.values)
    def test_worker_fuels_a_car_end_to_end_success(self, balance_source):
        # Given a car funded from one balance holder
        holder = self.fund(balance_source)

        # When the worker verifies the driver
        verified = verify(self.worker, self.driver, self.car)

        # Then a pending operation opens and the car is locked
        assert verified.status_code == status.HTTP_200_OK, verified.data
        # 1000 buys 90 L at 11/L (10 + 10% company fee); the car may take 40
        assert verified.data["car"]["liter_count"] == 40
        assert Decimal(verified.data["car"]["cost"]) == Decimal("440.00")
        operation = CarOperation.objects.get(id=verified.data["operation_id"])
        assert operation.status == CarOperation.OperationStatus.PENDING
        assert operation.worker_id == self.worker_user.id
        assert operation.station_branch_id == self.station_branch.id
        self.car.refresh_from_db()
        assert self.car.is_blocked_balance_update is True

        # When the worker starts the pump and reads the meter
        assert start_pump(self.worker, operation.id).status_code == status.HTTP_200_OK
        metered = read_meter(self.worker, operation.id, "10100")

        # Then the operation moves to in-progress
        assert metered.status_code == status.HTTP_200_OK, metered.data
        operation.refresh_from_db()
        assert operation.status == CarOperation.OperationStatus.IN_PROGRESS

        # When the worker pumps the fuel
        pumped = pump(self.worker, operation.id, "20")

        # Then the operation completes and every balance, khazna row and
        # notification reflects the fueling
        assert pumped.status_code == status.HTTP_200_OK, pumped.data
        operation.refresh_from_db()
        assert operation.status == CarOperation.OperationStatus.COMPLETED
        assert operation.cost == Decimal("200.00")
        assert operation.company_cost == Decimal("220.00")
        assert operation.station_cost == Decimal("210.00")
        assert operation.profits == Decimal("10.00")
        assert operation.car_first_meter == Decimal("10000.00")
        assert fresh_balance(holder) == Decimal("780.00")
        others = [item for item in self.holders() if item is not holder]
        assert [fresh_balance(item) for item in others] == [Decimal("0.00")] * 2
        assert fresh_balance(self.station_branch) == Decimal("290.00")
        self.car.refresh_from_db()
        assert self.car.is_blocked_balance_update is False
        assert self.car.last_meter == 10100
        company_txn = CompanyKhaznaTransaction.objects.get()
        assert company_txn.company_branch_id == self.company_branch.id
        assert company_txn.amount == Decimal("220.00")
        station_txn = StationKhaznaTransaction.objects.get()
        assert station_txn.station_branch_id == self.station_branch.id
        assert station_txn.amount == Decimal("210.00")
        # company MONEY goes to the car's branch managers, not the owner
        assert notification_user_ids(Notification.NotificationType.MONEY) == {
            self.station_owner.id,
            self.worker_user.id,
            self.company_manager.id,
        }

    def test_completed_fueling_shows_up_for_company_and_station_success(self):
        # Given a completed fueling
        self.fund(Car.BalanceSource.CAR)
        operation_id, _ = fuel(
            self.worker, self.driver, self.car, amount="20", meter="10100"
        )
        owner = sign_in("company", self.company_owner)
        station_owner = sign_in("station", self.station_owner)
        today = timezone.localdate().isoformat()

        # When the company and the station read their listings
        company_list = owner.get(operation_list_url())
        company_home = owner.get(company_home_url())
        station_list = station_owner.get(operations_url())
        report = station_owner.get(reports_url(date_from=today, date_to=today))

        # Then the operation and its totals appear on both sides
        assert ids(company_list.data["results"]) == [operation_id]
        assert ids(company_home.data["car_operations"]) == [operation_id]
        assert company_home.data["cars_balance"] == Decimal("780.00")
        assert ids(station_list.data["results"]) == [operation_id]
        assert station_list.data["petrol_balance"] == Decimal("210.00")
        assert report.data["operations"] == [
            {
                "service": self.car.service_id,
                "service_name": self.car.service.name,
                "total_balance": "210.00",
                "count": 1,
                "amount": "20.00",
                "unit": "لتر",
            }
        ]

    def test_meter_past_oil_change_notifies_company_success(self):
        # Given a car whose next oil change is due within this fill
        self.fund(Car.BalanceSource.CAR)
        self.car.next_oil_change_km = 10050
        self.car.save(update_fields=["next_oil_change_km"])

        # When the worker fuels it past that reading
        _, response = fuel(
            self.worker, self.driver, self.car, amount="20", meter="10100"
        )

        # Then the company gets the oil-change reminder
        assert response.status_code == status.HTTP_200_OK, response.data
        assert notification_user_ids(Notification.NotificationType.GENERAL) == {
            self.company_owner.id,
            self.company_manager.id,
        }

    def test_cancel_unlocks_car_for_a_new_visit_success(self):
        # Given a verified, still-open operation
        self.fund(Car.BalanceSource.CAR)
        operation_id = verify(self.worker, self.driver, self.car).data["operation_id"]

        # When the worker cancels it and verifies again
        cancelled = self.worker.delete(gas_url(operation_id))
        again = verify(self.worker, self.driver, self.car)

        # Then the car is unlocked and a fresh verify succeeds
        assert cancelled.status_code == status.HTTP_204_NO_CONTENT
        assert not CarOperation.objects.filter(id=operation_id).exists()
        assert again.status_code == status.HTTP_200_OK, again.data

    def test_verify_while_another_operation_is_open_fail(self):
        # Given a car already in an open operation
        self.fund(Car.BalanceSource.CAR)
        verify(self.worker, self.driver, self.car)

        # When the worker verifies it a second time
        response = verify(self.worker, self.driver, self.car)

        # Then the second verify is rejected
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "car_in_progress"
        assert CarOperation.objects.count() == 1

    def test_verify_on_a_day_the_car_may_not_fuel_fail(self):
        # Given a car only allowed to fuel tomorrow
        self.fund(Car.BalanceSource.CAR)
        tomorrow = (timezone.localtime() + timedelta(days=1)).strftime("%A")
        self.car.fuel_allowed_days = [tomorrow]
        self.car.save(update_fields=["fuel_allowed_days"])

        # When the worker verifies it today
        response = verify(self.worker, self.driver, self.car)

        # Then it is rejected and no operation opens
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == "car_not_active"
        assert not CarOperation.objects.exists()

    def test_verify_after_dashboard_suspends_company_fail(self, admin_user):
        # Given the dashboard has suspended the car's company
        self.fund(Car.BalanceSource.CAR)
        admin = sign_in("dashboard", admin_user)
        suspended = admin.patch(
            reverse("companies-detail", kwargs={"pk": self.company.id}),
            {"is_active": False},
            format="json",
        )

        # When the worker verifies the car
        response = verify(self.worker, self.driver, self.car)

        # Then verification is refused for the inactive company
        assert suspended.status_code == status.HTTP_200_OK, suspended.data
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == "company_not_active"

    def test_verify_driver_from_another_company_fail(
        self, driver_factory, other_company_branch
    ):
        # Given a driver belonging to a different company
        self.fund(Car.BalanceSource.CAR)
        stranger = driver_factory(branch=other_company_branch)

        # When the worker verifies that driver against this car
        response = verify(self.worker, stranger, self.car)

        # Then the mismatch is rejected
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == "driver_not_belongs_to_company"

    @pytest.mark.parametrize("balance_source", Car.BalanceSource.values)
    def test_verify_without_enough_balance_fail(self, balance_source):
        # Given a barely funded balance holder
        self.fund(balance_source, "5.00")

        # When the worker verifies the car
        response = verify(self.worker, self.driver, self.car)

        # Then it is rejected for insufficient balance
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == "not_enough_balance"
        assert not CarOperation.objects.exists()

    def test_verify_past_the_daily_fueling_limit_fail(self):
        # Given a car that has used its single daily fueling
        self.fund(Car.BalanceSource.CAR)
        self.car.number_of_fuelings_per_day = 1
        self.car.save(update_fields=["number_of_fuelings_per_day"])
        fuel(self.worker, self.driver, self.car, amount="20", meter="10100")

        # When the worker verifies it again the same day
        response = verify(self.worker, self.driver, self.car)

        # Then the daily limit blocks a new operation
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "car_in_progress"
        assert CarOperation.objects.count() == 1

    @pytest.mark.parametrize(
        ("holder_balance", "amount"),
        [
            ("1000.00", "41"),  # over the 40 L the car is permitted
            ("100.00", "10"),  # 100 buys 9 L at 11/L
        ],
    )
    def test_pump_more_than_available_liters_fail(self, holder_balance, amount):
        # Given a started operation on a car with limited liters
        self.fund(Car.BalanceSource.CAR, holder_balance)
        operation_id = start_fueling(self.worker, self.driver, self.car, meter="10100")

        # When the worker pumps more than the car may take
        response = pump(self.worker, operation_id, amount)

        # Then it is rejected and nothing is charged
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        operation = CarOperation.objects.get(id=operation_id)
        assert operation.status == CarOperation.OperationStatus.IN_PROGRESS
        assert fresh_balance(self.car) == Decimal(holder_balance)
        assert fresh_balance(self.station_branch) == Decimal("500.00")

    def test_pump_after_the_60_second_window_fail(self):
        # Given a started operation whose start time is over a minute ago
        self.fund(Car.BalanceSource.CAR)
        operation_id = start_fueling(self.worker, self.driver, self.car, meter="10100")
        # the worker took more than a minute between starting and finishing
        CarOperation.objects.filter(id=operation_id).update(
            start_time=F("start_time") - timedelta(seconds=61)
        )

        # When the worker pumps after the 60-second window
        response = pump(self.worker, operation_id, "20")

        # Then it is rejected and nothing is charged
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert fresh_balance(self.car) == Decimal("1000.00")
        assert not CompanyKhaznaTransaction.objects.exists()

    def test_meter_below_the_last_reading_fail(self):
        # Given a started operation on a car with a higher last meter
        self.fund(Car.BalanceSource.CAR)
        operation_id = verify(self.worker, self.driver, self.car).data["operation_id"]
        start_pump(self.worker, operation_id)

        # When the worker enters a meter below the last reading
        response = read_meter(self.worker, operation_id, "9999")

        # Then it is rejected and the operation stays pending
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        operation = CarOperation.objects.get(id=operation_id)
        assert operation.status == CarOperation.OperationStatus.PENDING

    def test_pump_again_after_completion_fail(self):
        # Given a completed fueling
        self.fund(Car.BalanceSource.CAR)
        operation_id, _ = fuel(
            self.worker, self.driver, self.car, amount="20", meter="10100"
        )

        # When the worker tries to pump the finished operation again
        response = pump(self.worker, operation_id, "20")

        # Then it is rejected and the balance is unchanged
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        assert fresh_balance(self.car) == Decimal("780.00")
