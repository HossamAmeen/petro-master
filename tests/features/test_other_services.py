"""A station worker sells a non-fuel service (a wash) to a company car."""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_models import Car
from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification
from apps.stations.models.service_models import Service
from apps.stations.tests.helpers import (
    image_file,
    notification_user_ids,
    operations_url,
    other_url,
)

from .helpers import complete_other_service, fresh_balance, sign_in, verify

pytestmark = [pytest.mark.django_db, pytest.mark.feature]


class TestOtherServices:
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
        branch,
        station_owner,
        station_worker,
        other_service,
        branch_other_service,
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
        self.wash = other_service
        set_balance(branch, "500.00")
        self.worker = sign_in("station", station_worker)

    def fund(self, balance_source=Car.BalanceSource.CAR, amount="1000.00"):
        self.car.balance_source = balance_source
        self.car.save(update_fields=["balance_source"])
        holder = self.car.balance_holder
        set_balance(holder, amount)
        return holder

    def complete(self, operation_id, cost="50.00", service=None, client=None):
        return (client or self.worker).patch(
            other_url(operation_id),
            {
                "service": (service or self.wash).id,
                "cost": cost,
                "car_image": image_file("car.png"),
            },
            format="multipart",
        )

    @pytest.mark.parametrize("balance_source", Car.BalanceSource.values)
    def test_worker_washes_a_car_end_to_end_success(self, balance_source):
        holder = self.fund(balance_source)

        verified = verify(self.worker, self.driver, self.car, "other")

        assert verified.status_code == status.HTTP_200_OK, verified.data
        assert verified.data["car"]["liter_count"] == 0
        operation = CarOperation.objects.get(id=verified.data["operation_id"])
        assert operation.service is None

        response = self.complete(operation.id)

        assert response.status_code == status.HTTP_200_OK, response.data
        operation.refresh_from_db()
        assert operation.status == CarOperation.OperationStatus.COMPLETED
        assert operation.service_id == self.wash.id
        assert operation.cost == Decimal("50.00")
        assert operation.unit == Service.ServiceUnit.UNIT
        # 50 + the company branch's 10% other-service fee
        assert fresh_balance(holder) == Decimal("945.00")
        # unlike fueling, the station branch balance is not touched
        assert fresh_balance(self.station_branch) == Decimal("500.00")
        assert CompanyKhaznaTransaction.objects.get().amount == Decimal("55.00")
        # 50 minus the station branch's 5% other-service fee
        assert StationKhaznaTransaction.objects.get().amount == Decimal("47.50")
        self.car.refresh_from_db()
        assert self.car.is_blocked_balance_update is False
        assert notification_user_ids(Notification.NotificationType.MONEY) == {
            self.station_owner.id,
            self.worker_user.id,
            self.company_owner.id,
            self.company_manager.id,
        }

    def test_completed_wash_is_missing_from_station_totals_fail(self):
        """Open issue: completing another service never stores `company_cost`,
        `station_cost` or `profits` on the operation, so the station's
        `other_balance` stays 0 although it earned 47.50."""
        self.fund()
        operation_id, _ = complete_other_service(
            self.worker, self.driver, self.car, service=self.wash, cost="50.00"
        )

        listed = sign_in("station", self.station_owner).get(operations_url())

        operation = CarOperation.objects.get(id=operation_id)
        assert operation.station_cost is None
        assert operation.company_cost is None
        assert listed.data["other_balance"] == 0

    def test_cancel_unlocks_the_car_success(self):
        self.fund()
        operation_id = verify(self.worker, self.driver, self.car, "other").data[
            "operation_id"
        ]

        response = self.worker.delete(other_url(operation_id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.car.refresh_from_db()
        assert self.car.is_blocked_balance_update is False

    def test_a_different_worker_cannot_complete_it_fail(self, second_station_worker):
        self.fund()
        operation_id = verify(self.worker, self.driver, self.car, "other").data[
            "operation_id"
        ]

        response = self.complete(
            operation_id, client=sign_in("station", second_station_worker)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        operation = CarOperation.objects.get(id=operation_id)
        assert operation.status == CarOperation.OperationStatus.PENDING
        assert fresh_balance(self.car) == Decimal("1000.00")

    def test_service_the_branch_does_not_offer_fail(self, service):
        self.fund()
        operation_id = verify(self.worker, self.driver, self.car, "other").data[
            "operation_id"
        ]

        response = self.complete(operation_id, service=service)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert fresh_balance(self.car) == Decimal("1000.00")

    @pytest.mark.parametrize("cost", ["0", "-5"])
    def test_cost_must_be_positive_fail(self, cost):
        self.fund()
        operation_id = verify(self.worker, self.driver, self.car, "other").data[
            "operation_id"
        ]

        response = self.complete(operation_id, cost=cost)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert fresh_balance(self.car) == Decimal("1000.00")

    def test_not_enough_balance_leaves_the_visit_open_fail(self):
        self.fund(amount="10.00")
        operation_id = verify(self.worker, self.driver, self.car, "other").data[
            "operation_id"
        ]

        response = self.complete(operation_id)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_enough_balance"
        operation = CarOperation.objects.get(id=operation_id)
        assert operation.status == CarOperation.OperationStatus.PENDING
        self.car.refresh_from_db()
        assert self.car.is_blocked_balance_update is True
        assert fresh_balance(self.car) == Decimal("10.00")
        assert not StationKhaznaTransaction.objects.exists()
