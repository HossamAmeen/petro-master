from datetime import timedelta
from decimal import Decimal
from functools import partial

import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_models import Car
from apps.companies.models.operation_model import CarOperation
from apps.notifications.models import Notification
from apps.stations.tests.helpers import (
    fund_balance_source,
    gas_costs,
    gas_url,
    image_file,
    notification_user_ids,
    prepare_gas_for_amount,
    set_balance,
    worker_client,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def configure_fuel_money(company_branch, branch, car, station, **overrides):
    company_branch.fees = Decimal(overrides.get("company_fees", "10.00"))
    company_branch.save(update_fields=["fees"])
    branch.fees = Decimal(overrides.get("station_fees", "0.50"))
    branch.save(update_fields=["fees"])
    set_balance(branch, overrides.get("branch_balance", "500.00"))
    set_balance(station, overrides.get("station_balance", "200.00"))
    car.balance = Decimal(overrides.get("car_balance", "1000.00"))
    car.is_blocked_balance_update = True
    car.save(update_fields=["balance", "is_blocked_balance_update"])


class TestStationGasOperationUpdate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, station_worker, station, company_branch, branch, car):
        self.worker = station_worker
        self.client = worker_client(auth_client, station_worker, station)
        self.configure_money = partial(
            configure_fuel_money, company_branch, branch, car, station
        )
        self.configure_money()

    def complete_amount(self, operation, amount="20", client=None):
        return (client or self.client).patch(
            gas_url(operation.id),
            {"amount": amount, "fuel_image": image_file("fuel.png")},
            format="multipart",
        )

    def test_patch_without_authentication_fail(self, api_client, gas_operation):
        response = api_client.patch(
            gas_url(gas_operation.id),
            {"start_time": timezone.localtime().isoformat()},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        gas_operation.refresh_from_db()
        assert gas_operation.start_time is None
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    def test_get_not_allowed_fail(self, gas_operation):
        response = self.client.get(gas_url(gas_operation.id))

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_patch_unknown_operation_fail(self):
        response = self.client.patch(
            gas_url(999_999),
            {"start_time": timezone.localtime().isoformat()},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"

    @pytest.mark.parametrize(
        "op_status",
        [
            CarOperation.OperationStatus.COMPLETED,
            CarOperation.OperationStatus.CANCELLED,
        ],
    )
    def test_patch_finished_operation_fail(self, op_status, gas_operation):
        gas_operation.status = op_status
        gas_operation.save(update_fields=["status"])

        response = self.client.patch(
            gas_url(gas_operation.id),
            {"start_time": timezone.localtime().isoformat()},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"

    def test_patch_start_time_success(self, gas_operation):
        before = timezone.localtime()

        response = self.client.patch(
            gas_url(gas_operation.id),
            {"start_time": "2020-01-01T00:00:00Z"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.start_time is not None
        assert gas_operation.start_time >= before
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    def test_patch_car_meter_without_motor_image_fail(self, gas_operation):
        response = self.client.patch(
            gas_url(gas_operation.id),
            {"car_meter": "10100"},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        gas_operation.refresh_from_db()
        assert gas_operation.car_meter is None
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    def test_patch_car_meter_negative_fail(self, gas_operation):
        response = self.client.patch(
            gas_url(gas_operation.id),
            {"car_meter": "-1", "motor_image": image_file("motor.png")},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        gas_operation.refresh_from_db()
        assert gas_operation.car_meter is None

    def test_patch_car_meter_below_last_meter_fail(self, gas_operation, car):
        response = self.client.patch(
            gas_url(gas_operation.id),
            {"car_meter": "9999", "motor_image": image_file("motor.png")},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING
        car.refresh_from_db()
        assert car.last_meter == 10000

    def test_patch_car_meter_equal_to_last_meter_success(self, gas_operation):
        response = self.client.patch(
            gas_url(gas_operation.id),
            {"car_meter": "10000", "motor_image": image_file("motor.png")},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.IN_PROGRESS
        assert gas_operation.car_meter == Decimal("10000.00")
        assert gas_operation.motor_image

    def test_patch_car_meter_without_odometer_below_last_meter_success(
        self, gas_operation, car
    ):
        car.is_with_odometer = False
        car.save(update_fields=["is_with_odometer"])

        response = self.client.patch(
            gas_url(gas_operation.id),
            {"car_meter": "10", "motor_image": image_file("motor.png")},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.IN_PROGRESS
        assert gas_operation.car_meter == Decimal("10.00")

    def test_patch_amount_without_fuel_image_fail(self, gas_operation):
        prepare_gas_for_amount(gas_operation)

        response = self.client.patch(
            gas_url(gas_operation.id),
            {"amount": "20"},
            format="multipart",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING
        assert gas_operation.amount is None

    def test_patch_amount_zero_fail(self, gas_operation):
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "0")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    def test_patch_amount_without_start_time_fail(self, gas_operation):
        gas_operation.car_meter = Decimal("10100")
        gas_operation.save(update_fields=["car_meter"])

        response = self.complete_amount(gas_operation)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    def test_patch_amount_after_sixty_seconds_fail(self, gas_operation):
        gas_operation.start_time = timezone.localtime() - timedelta(seconds=61)
        gas_operation.car_meter = Decimal("10100")
        gas_operation.save(update_fields=["start_time", "car_meter"])

        response = self.complete_amount(gas_operation)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    def test_patch_amount_above_tank_fail(self, gas_operation, car, branch):
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "51")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        gas_operation.refresh_from_db()
        car.refresh_from_db()
        branch.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING
        assert car.balance == Decimal("1000.00")
        assert branch.balance == Decimal("500.00")
        assert CompanyKhaznaTransaction.objects.count() == 0
        assert StationKhaznaTransaction.objects.count() == 0
        assert Notification.objects.count() == 0

    def test_patch_amount_above_permitted_fuel_fail(self, gas_operation, car):
        car.permitted_fuel_amount = 10
        car.save(update_fields=["permitted_fuel_amount"])
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "11")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    def test_patch_amount_above_balance_liters_fail(self, gas_operation, car):
        self.configure_money(car_balance="100.00")
        prepare_gas_for_amount(gas_operation)
        # company liter cost = 11, floor(100/11) = 9

        response = self.complete_amount(gas_operation, "10")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        car.refresh_from_db()
        assert car.balance == Decimal("100.00")

    def test_full_flow_completes_balances_transactions_and_notifications_success(
        self,
        station_worker,
        station,
        gas_operation,
        car,
        company_branch,
        branch,
        company,
        company_owner,
        company_branch_manager,
        station_owner,
        branch_manager,
        second_station_owner,
        other_station_owner,
        other_company_owner,
        second_branch_company_manager,
        finance_user,
    ):
        expected = gas_costs("20", gas_operation.service, company_branch, branch)

        start_response = self.client.patch(
            gas_url(gas_operation.id),
            {"start_time": timezone.localtime().isoformat()},
            format="json",
        )
        assert start_response.status_code == status.HTTP_200_OK, start_response.data

        meter_response = self.client.patch(
            gas_url(gas_operation.id),
            {"car_meter": "10100", "motor_image": image_file("motor.png")},
            format="multipart",
        )
        assert meter_response.status_code == status.HTTP_200_OK, meter_response.data
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.IN_PROGRESS

        amount_response = self.complete_amount(gas_operation, "20")
        assert amount_response.status_code == status.HTTP_200_OK, amount_response.data

        gas_operation.refresh_from_db()
        car.refresh_from_db()
        branch.refresh_from_db()
        station.refresh_from_db()
        company.refresh_from_db()

        assert gas_operation.status == CarOperation.OperationStatus.COMPLETED
        assert gas_operation.amount == Decimal("20.00")
        assert gas_operation.cost == expected["cost"]
        assert gas_operation.company_cost == expected["company_cost"]
        assert gas_operation.station_cost == expected["station_cost"]
        assert gas_operation.profits == expected["profits"]
        assert gas_operation.unit == gas_operation.service.unit
        assert gas_operation.end_time is not None
        assert gas_operation.duration >= 0
        assert gas_operation.car_first_meter == 10000
        assert gas_operation.fuel_image
        assert car.balance == Decimal("1000.00") - expected["company_cost"]
        assert car.last_meter == 10100
        assert car.is_blocked_balance_update is False
        assert car.fuel_consumption_rate == int(
            (gas_operation.car_meter - gas_operation.car_first_meter)
            / gas_operation.amount
        )
        assert branch.balance == Decimal("500.00") - expected["station_cost"]
        assert station.balance == Decimal("200.00")
        assert company.balance == Decimal("0.00")

        station_txn = StationKhaznaTransaction.objects.get()
        assert station_txn.station_id == station.id
        assert station_txn.station_branch_id == branch.id
        assert station_txn.amount == expected["station_cost"]
        assert station_txn.status == StationKhaznaTransaction.TransactionStatus.APPROVED
        assert station_txn.is_internal is False
        assert "ABC 1234" in station_txn.description
        assert "20" in station_txn.description

        company_txn = CompanyKhaznaTransaction.objects.get()
        assert company_txn.company_id == company.id
        assert company_txn.company_branch_id == company_branch.id
        assert company_txn.amount == expected["company_cost"]
        assert company_txn.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED
        assert company_txn.is_internal is True

        oil_users = notification_user_ids(
            Notification.NotificationType.GENERAL, "يجب تغيير زيت"
        )
        station_money_users = set(
            Notification.objects.filter(
                type=Notification.NotificationType.MONEY,
                title__contains="تم تفويل",
            )
            .exclude(title__contains="وخصم مبلغ")
            .values_list("user_id", flat=True)
        )
        company_money_users = notification_user_ids(
            Notification.NotificationType.MONEY, "وخصم مبلغ"
        )

        assert oil_users == set()
        assert station_money_users == {
            station_owner.id,
            branch_manager.id,
            second_station_owner.id,
            station_worker.id,
        }
        assert company_money_users == {
            company_branch_manager.id,
            station_worker.id,
        }
        assert company_owner.id not in company_money_users
        assert other_station_owner.id not in station_money_users
        assert other_company_owner.id not in company_money_users
        assert second_branch_company_manager.id not in company_money_users
        assert finance_user.id not in station_money_users | company_money_users

        worker_types = set(
            Notification.objects.filter(user_id=station_worker.id).values_list(
                "type", flat=True
            )
        )
        assert worker_types == {Notification.NotificationType.MONEY}
        assert Notification.objects.filter(user_id=station_worker.id).count() == 2

    def test_complete_sends_oil_change_to_company_owner_and_branch_manager_success(
        self,
        station_worker,
        gas_operation,
        car,
        company_owner,
        company_branch_manager,
        second_branch_company_manager,
        other_company_owner,
        station_owner,
    ):
        car.next_oil_change_km = 10050
        car.save(update_fields=["next_oil_change_km"])
        prepare_gas_for_amount(gas_operation, meter="10100")

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        oil_users = notification_user_ids(
            Notification.NotificationType.GENERAL, "يجب تغيير زيت"
        )
        assert oil_users == {company_owner.id, company_branch_manager.id}
        assert second_branch_company_manager.id not in oil_users
        assert other_company_owner.id not in oil_users
        assert station_owner.id not in oil_users
        assert station_worker.id not in oil_users
        oil = Notification.objects.filter(
            type=Notification.NotificationType.GENERAL
        ).first()
        assert "ABC 1234" in oil.title
        assert "20" in oil.title

    def test_complete_does_not_send_oil_change_when_meter_below_threshold_success(
        self, gas_operation, car, company_owner
    ):
        car.next_oil_change_km = 20000
        car.save(update_fields=["next_oil_change_km"])
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        assert (
            Notification.objects.filter(
                type=Notification.NotificationType.GENERAL
            ).count()
            == 0
        )
        assert company_owner.id not in notification_user_ids(
            Notification.NotificationType.MONEY, "وخصم مبلغ"
        )

    def test_complete_at_available_liter_limit_success(
        self, gas_operation, car, company_branch, branch
    ):
        car.permitted_fuel_amount = 10
        car.save(update_fields=["permitted_fuel_amount"])
        prepare_gas_for_amount(gas_operation)
        expected = gas_costs("10", gas_operation.service, company_branch, branch)

        response = self.complete_amount(gas_operation, "10")

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        car.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.COMPLETED
        assert gas_operation.company_cost == expected["company_cost"]
        assert car.balance == Decimal("1000.00") - expected["company_cost"]

    def test_complete_uses_tank_capacity_when_permitted_is_zero_success(
        self, gas_operation, car
    ):
        car.permitted_fuel_amount = 0
        car.tank_capacity = 15
        car.save(update_fields=["permitted_fuel_amount", "tank_capacity"])
        prepare_gas_for_amount(gas_operation)

        too_much = self.complete_amount(gas_operation, "16")
        assert too_much.status_code == status.HTTP_400_BAD_REQUEST

        prepare_gas_for_amount(gas_operation)
        ok = self.complete_amount(gas_operation, "15")
        assert ok.status_code == status.HTTP_200_OK, ok.data

    def test_complete_without_odometer_skips_consumption_rate_success(
        self, gas_operation, car
    ):
        car.is_with_odometer = False
        car.fuel_consumption_rate = 9
        car.save(update_fields=["is_with_odometer", "fuel_consumption_rate"])
        prepare_gas_for_amount(gas_operation, meter="10100")

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        car.refresh_from_db()
        assert car.last_meter == 10100
        assert car.fuel_consumption_rate == 9

    def test_complete_by_another_authenticated_worker_success(
        self, auth_client, second_station_worker, station, gas_operation
    ):
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(
            gas_operation,
            "20",
            client=auth_client(second_station_worker, station_id=station.id),
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.COMPLETED
        assert gas_operation.worker_id == gas_operation.worker_id
        station_money_users = set(
            Notification.objects.filter(
                type=Notification.NotificationType.MONEY,
                title__contains="تم تفويل",
            )
            .exclude(title__contains="وخصم مبلغ")
            .values_list("user_id", flat=True)
        )
        assert second_station_worker.id in station_money_users

    def test_complete_can_drive_station_branch_balance_negative_success(
        self, gas_operation, company_branch, branch
    ):
        self.configure_money(branch_balance="1.00")
        prepare_gas_for_amount(gas_operation)
        expected = gas_costs("20", gas_operation.service, company_branch, branch)

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        branch.refresh_from_db()
        assert branch.balance == Decimal("1.00") - expected["station_cost"]
        assert branch.balance < 0

    def test_post_and_put_not_allowed_fail(self, gas_operation):
        client = self.client

        assert (
            client.post(gas_url(gas_operation.id), {}, format="json").status_code
            == status.HTTP_405_METHOD_NOT_ALLOWED
        )
        assert (
            client.put(gas_url(gas_operation.id), {}, format="json").status_code
            == status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_patch_empty_payload_leaves_pending_success(self, gas_operation):
        response = self.client.patch(gas_url(gas_operation.id), {}, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.PENDING
        assert gas_operation.start_time is None
        assert gas_operation.amount is None

    def test_patch_car_meter_takes_precedence_over_amount_success(
        self, gas_operation, car
    ):
        prepare_gas_for_amount(gas_operation)

        response = self.client.patch(
            gas_url(gas_operation.id),
            {
                "car_meter": "10100",
                "motor_image": image_file("motor.png"),
                "amount": "20",
                "fuel_image": image_file("fuel.png"),
            },
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        car.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.IN_PROGRESS
        assert car.balance == Decimal("1000.00")
        assert CompanyKhaznaTransaction.objects.count() == 0

    def test_patch_amount_within_sixty_seconds_success(self, gas_operation):
        gas_operation.start_time = timezone.localtime() - timedelta(seconds=59)
        gas_operation.car_meter = Decimal("10100")
        gas_operation.save(update_fields=["start_time", "car_meter"])

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.COMPLETED

    def test_patch_car_meter_zero_success(self, gas_operation, car):
        car.is_with_odometer = False
        car.save(update_fields=["is_with_odometer"])

        response = self.client.patch(
            gas_url(gas_operation.id),
            {"car_meter": "0", "motor_image": image_file("motor.png")},
            format="multipart",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.car_meter == Decimal("0.00")
        assert gas_operation.status == CarOperation.OperationStatus.IN_PROGRESS

    def test_complete_with_zero_fees_success(
        self, gas_operation, car, company_branch, branch
    ):
        self.configure_money(company_fees="0.00", station_fees="0.00")
        prepare_gas_for_amount(gas_operation)
        expected = gas_costs("20", gas_operation.service, company_branch, branch)

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        car.refresh_from_db()
        assert expected["company_cost"] == Decimal("200.00")
        assert expected["station_cost"] == Decimal("200.00")
        assert expected["profits"] == Decimal("0.00")
        assert gas_operation.profits == Decimal("0.00")
        assert car.balance == Decimal("800.00")

    def test_oil_change_at_exact_meter_threshold_success(
        self, gas_operation, car, company_owner, company_branch_manager
    ):
        car.next_oil_change_km = 10100
        car.save(update_fields=["next_oil_change_km"])
        prepare_gas_for_amount(gas_operation, meter="10100")

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        oil_users = notification_user_ids(
            Notification.NotificationType.GENERAL, "يجب تغيير زيت"
        )
        assert oil_users == {company_owner.id, company_branch_manager.id}

    def test_oil_change_skipped_when_next_km_is_zero_success(self, gas_operation, car):
        car.next_oil_change_km = 0
        car.save(update_fields=["next_oil_change_km"])
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        assert (
            Notification.objects.filter(
                type=Notification.NotificationType.GENERAL
            ).count()
            == 0
        )

    @pytest.mark.parametrize("role_fixture", ["admin_user", "company_owner"])
    def test_complete_as_authenticated_non_worker_success(
        self, role_fixture, request, auth_client, station, gas_operation, company
    ):
        user = request.getfixturevalue(role_fixture)
        prepare_gas_for_amount(gas_operation)
        kwargs = {"station_id": station.id}
        if role_fixture == "company_owner":
            kwargs["company_id"] = company.id

        response = self.complete_amount(
            gas_operation, "20", client=auth_client(user, **kwargs)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.COMPLETED
        assert user.id in notification_user_ids(
            Notification.NotificationType.MONEY, "تم تفويل"
        )

    def test_complete_diesel_service_success(
        self,
        station_worker,
        car,
        driver,
        branch,
        diesel_service,
        company_branch,
        car_operation_factory,
    ):
        operation = car_operation_factory(
            car=car,
            driver=driver,
            station_branch=branch,
            worker=station_worker,
            service=diesel_service,
            status=CarOperation.OperationStatus.PENDING,
            amount=None,
        )
        prepare_gas_for_amount(operation)
        expected = gas_costs("10", diesel_service, company_branch, branch)

        response = self.complete_amount(operation, "10")

        assert response.status_code == status.HTTP_200_OK, response.data
        operation.refresh_from_db()
        car.refresh_from_db()
        assert operation.status == CarOperation.OperationStatus.COMPLETED
        assert operation.company_cost == expected["company_cost"]
        assert car.balance == Decimal("1000.00") - expected["company_cost"]

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_complete_deducts_from_the_configured_holder_success(
        self, balance_source, gas_operation, car, company_branch, branch, company
    ):
        holder = fund_balance_source(car, company_branch, company, balance_source)
        expected = gas_costs("20", gas_operation.service, company_branch, branch)
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        gas_operation.refresh_from_db()
        car.refresh_from_db()
        holder.refresh_from_db()
        assert gas_operation.status == CarOperation.OperationStatus.COMPLETED
        assert gas_operation.company_cost == expected["company_cost"]
        assert car.balance == Decimal("0.00")
        assert car.is_blocked_balance_update is False
        assert holder.balance == Decimal("1000.00") - expected["company_cost"]

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_complete_leaves_the_other_company_balances_untouched_success(
        self, balance_source, gas_operation, car, company_branch, company
    ):
        fund_balance_source(
            car, company_branch, company, balance_source, car_balance="500.00"
        )
        untouched = (
            company if balance_source == Car.BalanceSource.BRANCH else company_branch
        )
        set_balance(untouched, "700.00")

        response = self.complete_amount(prepare_gas_for_amount(gas_operation), "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        car.refresh_from_db()
        untouched.refresh_from_db()
        assert car.balance == Decimal("500.00")
        assert untouched.balance == Decimal("700.00")

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_patch_amount_above_holder_balance_fail(
        self, balance_source, gas_operation, car, company_branch, company
    ):
        holder = fund_balance_source(
            car, company_branch, company, balance_source, holder_balance="100.00"
        )
        prepare_gas_for_amount(gas_operation)
        # company liter cost = 11, floor(100/11) = 9

        response = self.complete_amount(gas_operation, "10")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        holder.refresh_from_db()
        gas_operation.refresh_from_db()
        assert holder.balance == Decimal("100.00")
        assert gas_operation.status == CarOperation.OperationStatus.PENDING

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_patch_amount_ignores_car_balance_when_funded_elsewhere_fail(
        self, balance_source, gas_operation, car, company_branch, company
    ):
        fund_balance_source(
            car,
            company_branch,
            company,
            balance_source,
            car_balance="5000.00",
            holder_balance="0.00",
        )
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "10")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
        car.refresh_from_db()
        assert car.balance == Decimal("5000.00")

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_complete_at_exact_holder_balance_success(
        self, balance_source, gas_operation, car, company_branch, company
    ):
        holder = fund_balance_source(
            car, company_branch, company, balance_source, holder_balance="110.00"
        )
        prepare_gas_for_amount(gas_operation)
        # company liter cost = 11, floor(110/11) = 10

        response = self.complete_amount(gas_operation, "10")

        assert response.status_code == status.HTTP_200_OK, response.data
        holder.refresh_from_db()
        assert holder.balance == Decimal("0.00")

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_complete_still_records_the_company_transaction_success(
        self, balance_source, gas_operation, car, company_branch, branch, company
    ):
        fund_balance_source(car, company_branch, company, balance_source)
        expected = gas_costs("20", gas_operation.service, company_branch, branch)
        prepare_gas_for_amount(gas_operation)

        response = self.complete_amount(gas_operation, "20")

        assert response.status_code == status.HTTP_200_OK, response.data
        company_txn = CompanyKhaznaTransaction.objects.get()
        assert company_txn.company_id == company.id
        assert company_txn.company_branch_id == company_branch.id
        assert company_txn.amount == expected["company_cost"]
        assert StationKhaznaTransaction.objects.count() == 1
