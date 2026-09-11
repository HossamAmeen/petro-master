"""Two companies and two stations, fully set up: neither can see the other's data."""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.accounting.tests.api.v1.company_transaction.helpers import (
    company_transaction_detail_url,
)
from apps.accounting.tests.api.v1.station_transaction.helpers import (
    station_transaction_detail_url,
)
from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car.helpers import car_detail_url, verify_url
from apps.companies.tests.api.v1.car_operation.helpers import operation_detail_url
from apps.companies.tests.helpers import set_balance
from apps.stations.tests.helpers import operations_url

from .helpers import ALL_DAYS, sign_in

pytestmark = [pytest.mark.django_db, pytest.mark.feature]


def ids(response):
    return {item["id"] for item in response.data["results"]}


def make_station_transaction(admin_user, station, station_branch, reference_code):
    return StationKhaznaTransaction.objects.create(
        station=station,
        station_branch=station_branch,
        amount=Decimal("10.00"),
        status=StationKhaznaTransaction.TransactionStatus.APPROVED,
        reference_code=reference_code,
        created_by=admin_user,
        updated_by=admin_user,
    )


class TestTenantIsolation:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        admin_user,
        company,
        company_owner,
        other_company,
        other_company_owner,
        other_company_branch,
        car_factory,
        driver_factory,
        car_operation_factory,
        company_transaction_factory,
        branch,
        station_owner,
        other_station,
        other_station_owner,
        other_station_branch,
        service,
    ):
        # tenant A
        self.car_a = car_factory(fuel_allowed_days=ALL_DAYS)
        self.driver_a = driver_factory()
        self.operation_a = car_operation_factory(
            car=self.car_a, status=CarOperation.OperationStatus.COMPLETED
        )
        self.company_txn_a = company_transaction_factory()
        self.station_txn_a = make_station_transaction(
            admin_user, branch.station, branch, "TENANT-A"
        )
        self.company_owner_a = sign_in("company", company_owner)
        self.station_owner_a = sign_in("station", station_owner)

        # tenant B
        self.car_b = car_factory(
            branch=other_company_branch, fuel_allowed_days=ALL_DAYS
        )
        self.driver_b = driver_factory(branch=other_company_branch)
        self.operation_b = car_operation_factory(
            car=self.car_b,
            driver=self.driver_b,
            station_branch=other_station_branch,
            status=CarOperation.OperationStatus.COMPLETED,
            service=service,
        )
        self.company_txn_b = company_transaction_factory(
            company=other_company, company_branch=other_company_branch
        )
        self.station_txn_b = make_station_transaction(
            admin_user, other_station, other_station_branch, "TENANT-B"
        )
        self.company_owner_b = sign_in("company", other_company_owner)
        self.station_owner_b = sign_in("station", other_station_owner)

    def test_company_owner_lists_only_their_own_records_success(self):
        cars = ids(self.company_owner_a.get(reverse("cars-list")))
        drivers = ids(self.company_owner_a.get(reverse("drivers-list")))
        operations = ids(self.company_owner_a.get(reverse("car-operations-list")))
        transactions = ids(
            self.company_owner_a.get(reverse("company-khazna-transactions-list"))
        )

        # the fixtures seed extra tenant-A helper records, so assert the
        # tenant-B records are excluded and the tenant-A ones are present
        assert self.car_a.id in cars and self.car_b.id not in cars
        assert self.driver_a.id in drivers and self.driver_b.id not in drivers
        assert operations == {self.operation_a.id}
        assert transactions == {self.company_txn_a.id}

    @pytest.mark.parametrize(
        ("url_builder", "target"),
        [
            (car_detail_url, "car_b"),
            (operation_detail_url, "operation_b"),
            (company_transaction_detail_url, "company_txn_b"),
        ],
    )
    def test_company_owner_cannot_reach_the_other_tenant_fail(
        self, url_builder, target
    ):
        obj = getattr(self, target)

        response = self.company_owner_a.get(url_builder(obj.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_station_owner_lists_only_their_own_records_success(self):
        operations = self.station_owner_a.get(operations_url())
        transactions = self.station_owner_a.get(
            reverse("station-khazna-transactions-list")
        )

        assert ids(operations) == {self.operation_a.id}
        assert ids(transactions) == {self.station_txn_a.id}

    def test_station_owner_cannot_reach_the_other_tenant_fail(self):
        transaction = self.station_owner_a.get(
            station_transaction_detail_url(self.station_txn_b.id)
        )

        assert transaction.status_code == status.HTTP_404_NOT_FOUND

    def test_worker_can_fuel_across_tenants_fail(
        self, station_worker, station, company_driver
    ):
        """Open boundary: gas PATCH and verify-driver only check authentication,
        so tenant A's worker can start an operation on tenant B's car."""
        set_balance(self.car_b, "1000.00")
        worker = sign_in("station", station_worker)

        response = worker.post(
            verify_url(self.driver_b.code, self.car_b.code, "petrol")
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        operation = CarOperation.objects.get(id=response.data["operation_id"])
        assert operation.car_id == self.car_b.id
        # the operation is booked against A's worker and branch
        assert operation.worker_id == station_worker.id
        assert operation.station_branch_id == station.branches.first().id
