"""Operations entered from the dashboard or cloned in the Django admin must move
money exactly like an operation made at the station."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_models import Car
from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import (
    operation_detail_url,
    operation_list_url,
)
from apps.companies.tests.helpers import set_balance

from .helpers import ALL_DAYS, fresh_balance, fuel, sign_in

pytestmark = [pytest.mark.django_db, pytest.mark.feature]

MONEY_FIELDS = ("cost", "company_cost", "station_cost", "profits")


def money(operation):
    return [getattr(operation, field) for field in MONEY_FIELDS]


class TestDashboardOperations:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        fees,
        fuelable_car,
        company_driver,
        branch,
        station_worker,
        service,
        admin_user,
    ):
        self.car = fuelable_car
        self.driver = company_driver
        self.station_branch = branch
        self.worker_user = station_worker
        self.service = service
        set_balance(self.car, "1000.00")
        set_balance(branch, "500.00")
        self.admin = sign_in("dashboard", admin_user)

    def operation_payload(self, car, **overrides):
        start = timezone.localtime()
        payload = {
            "car": car.id,
            "driver": self.driver.id,
            "station_branch": self.station_branch.id,
            "worker": self.worker_user.id,
            "service": self.service.id,
            "amount": "20.00",
            "car_meter": "10100.00",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=2)).isoformat(),
            "status": CarOperation.OperationStatus.COMPLETED,
            "fuel_type": Car.FuelType.GASOLINE,
        }
        payload.update(overrides)
        return payload

    def complete_payload(self, operation):
        return {
            "car": operation.car_id,
            "station_branch": operation.station_branch_id,
            "service": operation.service_id,
            "car_meter": "10100.00",
            "status": CarOperation.OperationStatus.COMPLETED,
        }

    def test_dashboard_operation_charges_like_a_station_fueling_success(
        self, car_factory
    ):
        other_car = car_factory(fuel_allowed_days=ALL_DAYS, last_meter=10000)
        set_balance(other_car, "1000.00")
        station_id, _ = fuel(
            sign_in("station", self.worker_user),
            self.driver,
            self.car,
            amount="20",
            meter="10100",
        )

        response = self.admin.post(
            operation_list_url(), self.operation_payload(other_car), format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        station_made = CarOperation.objects.get(id=station_id)
        dashboard_made = CarOperation.objects.exclude(id=station_id).get()
        assert money(dashboard_made) == money(station_made)
        assert fresh_balance(other_car) == fresh_balance(self.car) == Decimal("780.00")
        # 210 for each of the two fuelings
        assert fresh_balance(self.station_branch) == Decimal("80.00")
        assert CompanyKhaznaTransaction.objects.count() == 2
        assert StationKhaznaTransaction.objects.count() == 2

    def test_pending_operation_is_charged_once_when_completed_success(self):
        created = self.admin.post(
            operation_list_url(),
            self.operation_payload(
                self.car, status=CarOperation.OperationStatus.PENDING
            ),
            format="json",
        )
        operation = CarOperation.objects.get()
        # the car is charged on create, the station only on completion
        car_after_create = fresh_balance(self.car)
        station_after_create = fresh_balance(self.station_branch)

        completed = self.admin.patch(
            operation_detail_url(operation.id),
            self.complete_payload(operation),
            format="json",
        )

        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert car_after_create == Decimal("780.00")
        assert station_after_create == Decimal("500.00")
        assert completed.status_code == status.HTTP_200_OK, completed.data
        assert fresh_balance(self.car) == Decimal("780.00")
        assert fresh_balance(self.station_branch) == Decimal("290.00")
        assert CompanyKhaznaTransaction.objects.count() == 1
        assert StationKhaznaTransaction.objects.count() == 1

    def test_admin_clones_an_operation_success(self, local_cache, admin_client):
        source_id, _ = fuel(
            sign_in("station", self.worker_user),
            self.driver,
            self.car,
            amount="20",
            meter="10100",
        )

        response = admin_client.post(
            reverse("admin:companies_caroperation_clone", args=[source_id]),
            {"amount": "10.00"},
        )

        assert response.status_code == 302
        clone = CarOperation.objects.exclude(id=source_id).get()
        assert clone.amount == Decimal("10.00")
        assert money(clone) == [
            Decimal("100.00"),
            Decimal("110.00"),
            Decimal("105.00"),
            Decimal("5.00"),
        ]
        assert fresh_balance(self.car) == Decimal("670.00")
        assert fresh_balance(self.station_branch) == Decimal("185.00")
        assert CompanyKhaznaTransaction.objects.count() == 2
        assert StationKhaznaTransaction.objects.count() == 2

    def test_clone_more_than_the_car_can_take_fail(self, local_cache, admin_client):
        source_id, _ = fuel(
            sign_in("station", self.worker_user),
            self.driver,
            self.car,
            amount="20",
            meter="10100",
        )

        response = admin_client.post(
            reverse("admin:companies_caroperation_clone", args=[source_id]),
            {"amount": "500.00"},
        )

        assert response.status_code == 200
        assert response.context["form"].errors["amount"]
        assert CarOperation.objects.count() == 1
        assert fresh_balance(self.car) == Decimal("780.00")

    def test_company_owner_cannot_enter_operations_fail(self, company, company_owner):
        owner = sign_in("company", company_owner)

        response = owner.post(
            operation_list_url(), self.operation_payload(self.car), format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not CarOperation.objects.exists()

    def test_dashboard_operation_over_available_liters_fail(self):
        response = self.admin.post(
            operation_list_url(),
            self.operation_payload(self.car, amount="41.00"),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CarOperation.objects.exists()
        assert fresh_balance(self.car) == Decimal("1000.00")

    def test_completed_operation_cannot_change_or_be_deleted_fail(self):
        self.admin.post(
            operation_list_url(), self.operation_payload(self.car), format="json"
        )
        operation = CarOperation.objects.get()

        changed = self.admin.patch(
            operation_detail_url(operation.id),
            self.complete_payload(operation),
            format="json",
        )
        deleted = self.admin.delete(operation_detail_url(operation.id))

        assert changed.status_code == status.HTTP_400_BAD_REQUEST
        assert deleted.status_code == status.HTTP_400_BAD_REQUEST
        assert CarOperation.objects.filter(id=operation.id).exists()
        assert StationKhaznaTransaction.objects.count() == 1
