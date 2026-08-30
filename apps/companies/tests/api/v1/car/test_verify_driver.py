import math
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.companies.models.company_models import Car
from apps.companies.models.operation_model import CarOperation
from apps.stations.models.service_models import Service


pytestmark = [pytest.mark.api, pytest.mark.django_db]

BLOCKING_STATUSES = [
    CarOperation.OperationStatus.PENDING,
    CarOperation.OperationStatus.IN_PROGRESS,
]
NON_BLOCKING_STATUSES = [
    CarOperation.OperationStatus.COMPLETED,
    CarOperation.OperationStatus.CANCELLED,
]


def today_weekday():
    return timezone.localtime().strftime("%A")


def verify_url(driver_code, car_code, service_type="petrol"):
    return reverse(
        "verify-driver",
        kwargs={
            "driver_code": driver_code,
            "car_code": car_code,
            "service_type": service_type,
        },
    )


def worker_client(auth_client, station_worker, station):
    return auth_client(station_worker, station_id=station.id)


def verifiable_car(car_factory, **overrides):
    defaults = {
        "fuel_allowed_days": [today_weekday()],
        "balance": Decimal("1000.00"),
        "number_of_fuelings_per_day": 2,
    }
    defaults.update(overrides)
    return car_factory(**defaults)


def petrol_quote(car):
    service_cost = Decimal(str(car.service.cost))
    fees = Decimal(str(car.branch.fees))
    liter_cost = (service_cost * fees / 100) + service_cost
    liters_count = (
        car.permitted_fuel_amount if car.permitted_fuel_amount else car.tank_capacity
    )
    available_liters = min(liters_count, math.floor(car.balance / liter_cost))
    return available_liters, available_liters * liter_cost


def assert_error(response, status_code, code):
    assert response.status_code == status_code
    assert response.data["code"] == code


class TestCarVerifyDriver:


    def test_verify_driver_without_authentication_fail(self,
        api_client, company_driver, car_factory
    ):
        car = verifiable_car(car_factory)

        response = api_client.post(verify_url(company_driver.code, car.code))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CarOperation.objects.count() == 0


    @pytest.mark.parametrize(
        "role_fixture",
        [
            "admin_user",
            "company_owner",
            "company_branch_manager",
            "station_owner",
            "branch_manager",
        ],
    )
    def test_verify_driver_forbidden_role_fail(self,
        role_fixture,
        request,
        auth_client,
        company,
        station,
        company_driver,
        car_factory,
    ):
        user = request.getfixturevalue(role_fixture)
        car = verifiable_car(car_factory)
        client_kwargs = {}
        if role_fixture in {"company_owner", "company_branch_manager"}:
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "branch_manager"}:
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CarOperation.objects.count() == 0


    def test_verify_driver_get_not_allowed_fail(self, auth_client, station_worker, station):
        response = worker_client(auth_client, station_worker, station).get(
            verify_url("DRV", "CAR")
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


    def test_verify_driver_petrol_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        service,
    ):
        car = verifiable_car(car_factory)
        expected_liters, expected_cost = petrol_quote(car)

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        car.refresh_from_db()
        operation = CarOperation.objects.get(pk=response.data["operation_id"])
        assert response.data["message"] == "تم التحقق من السائق بنجاح"
        assert response.data["car"] == {
            "plate_number": car.plate_number,
            "plate_character": car.plate_character,
            "plate_color": car.plate_color,
            "fuel_type": car.fuel_type,
            "liter_count": expected_liters,
            "cost": expected_cost,
            "code": car.code,
            "service": {"name": service.name},
        }
        assert operation.car_id == car.id
        assert operation.driver_id == company_driver.id
        assert operation.service_id == service.id
        assert operation.worker_id == station_worker.id
        assert operation.station_branch_id == station_worker.station_branch_id
        assert operation.status == CarOperation.OperationStatus.PENDING
        assert operation.created_by_id == station_worker.id
        assert car.is_blocked_balance_update is True


    def test_verify_driver_same_company_other_branch_success(self,
        auth_client,
        station_worker,
        station,
        driver_factory,
        second_company_branch,
        car_factory,
    ):
        car = verifiable_car(car_factory)
        driver = driver_factory(branch=second_company_branch)

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert CarOperation.objects.get(pk=response.data["operation_id"]).driver_id == (
            driver.id
        )


    @pytest.mark.parametrize("service_type", ["other", "wash", "diesel"])
    def test_verify_driver_non_petrol_success(self,
        service_type,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory, balance=Decimal("0.00"))

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code, service_type)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        operation = CarOperation.objects.get(pk=response.data["operation_id"])
        assert response.data["car"]["liter_count"] == 0
        assert response.data["car"]["cost"] == Decimal("0.00")
        assert response.data["car"]["service"] == {"name": "-"}
        assert operation.service_id is None
        assert operation.status == CarOperation.OperationStatus.PENDING


    def test_verify_driver_non_petrol_uses_full_balance_as_cost_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory, balance=Decimal("250.50"))

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code, "other")
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["car"]["cost"] == Decimal("250.50")
        assert response.data["car"]["liter_count"] == 0


    def test_verify_driver_petrol_with_branch_fees_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        company_branch,
        car_factory,
    ):
        company_branch.fees = Decimal("10.00")
        company_branch.save(update_fields=["fees"])
        car = verifiable_car(car_factory, balance=Decimal("100.00"))
        expected_liters, expected_cost = petrol_quote(car)

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert expected_liters == 9
        assert response.data["car"]["liter_count"] == expected_liters
        assert response.data["car"]["cost"] == expected_cost


    def test_verify_driver_petrol_capped_by_permitted_fuel_amount_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(
            car_factory,
            balance=Decimal("1000.00"),
            permitted_fuel_amount=5,
            tank_capacity=60,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["car"]["liter_count"] == 5
        assert response.data["car"]["cost"] == Decimal("50.00")


    def test_verify_driver_petrol_uses_tank_capacity_when_permitted_is_zero_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(
            car_factory,
            balance=Decimal("1000.00"),
            permitted_fuel_amount=0,
            tank_capacity=8,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["car"]["liter_count"] == 8
        assert response.data["car"]["cost"] == Decimal("80.00")


    def test_verify_driver_petrol_exact_one_liter_balance_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory, balance=Decimal("10.00"))

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["car"]["liter_count"] == 1
        assert response.data["car"]["cost"] == Decimal("10.00")


    def test_verify_driver_strips_codes_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory)

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(f" {company_driver.code} ", f" {car.code} ")
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert CarOperation.objects.filter(car=car, driver=company_driver).exists()


    def test_verify_driver_unknown_car_code_fail(self,
        auth_client, station_worker, station, company_driver
    ):
        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, "UNKNOWNCAR")
        )

        assert_error(response, status.HTTP_404_NOT_FOUND, "car_code_not_found")
        assert CarOperation.objects.count() == 0


    def test_verify_driver_inactive_company_fail(self,
        auth_client,
        station_worker,
        station,
        company,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory)
        company.is_active = False
        company.save(update_fields=["is_active"])

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert_error(response, status.HTTP_404_NOT_FOUND, "company_not_active")
        car.refresh_from_db()
        assert CarOperation.objects.count() == 0
        assert car.is_blocked_balance_update is False


    def test_verify_driver_unknown_driver_code_fail(self,
        auth_client, station_worker, station, car_factory
    ):
        car = verifiable_car(car_factory)

        response = worker_client(auth_client, station_worker, station).post(
            verify_url("UNKNOWNDRV", car.code)
        )

        assert_error(response, status.HTTP_404_NOT_FOUND, "driver_code_not_found")
        car.refresh_from_db()
        assert CarOperation.objects.count() == 0
        assert car.is_blocked_balance_update is False


    def test_verify_driver_other_company_driver_fail(self,
        auth_client,
        station_worker,
        station,
        driver_factory,
        other_company_branch,
        car_factory,
    ):
        car = verifiable_car(car_factory)
        other_driver = driver_factory(branch=other_company_branch)

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(other_driver.code, car.code)
        )

        assert_error(response, status.HTTP_404_NOT_FOUND, "driver_not_belongs_to_company")
        car.refresh_from_db()
        assert CarOperation.objects.count() == 0
        assert car.is_blocked_balance_update is False


    @pytest.mark.parametrize("operation_status", BLOCKING_STATUSES)
    def test_verify_driver_car_already_in_progress_fail(self,
        operation_status,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        car_operation_factory,
        service,
    ):
        car = verifiable_car(car_factory)
        existing = car_operation_factory(
            car=car,
            driver=company_driver,
            service=service,
            status=operation_status,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert_error(response, status.HTTP_400_BAD_REQUEST, "car_in_progress")
        car.refresh_from_db()
        assert CarOperation.objects.filter(car=car).count() == 1
        assert CarOperation.objects.get(pk=existing.id).status == operation_status
        assert car.is_blocked_balance_update is False


    @pytest.mark.parametrize("operation_status", NON_BLOCKING_STATUSES)
    def test_verify_driver_non_blocking_operation_status_success(self,
        operation_status,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        car_operation_factory,
        other_service,
    ):
        car = verifiable_car(car_factory, number_of_fuelings_per_day=2)
        car_operation_factory(
            car=car,
            driver=company_driver,
            service=other_service,
            status=operation_status,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert CarOperation.objects.filter(car=car).count() == 2
        assert (
            CarOperation.objects.get(pk=response.data["operation_id"]).status
            == CarOperation.OperationStatus.PENDING
        )


    def test_verify_driver_car_not_allowed_today_fail(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        today = today_weekday()
        other_day = next(day for day in Car.FuelAllowedDay.values if day != today)
        car = verifiable_car(car_factory, fuel_allowed_days=[other_day])

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert_error(response, status.HTTP_404_NOT_FOUND, "car_not_active")
        car.refresh_from_db()
        assert CarOperation.objects.count() == 0
        assert car.is_blocked_balance_update is False


    def test_verify_driver_empty_fuel_allowed_days_fail(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory, fuel_allowed_days=[])

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert_error(response, status.HTTP_404_NOT_FOUND, "car_not_active")
        assert CarOperation.objects.count() == 0


    @pytest.mark.parametrize("balance", [Decimal("0.00"), Decimal("9.99")])
    def test_verify_driver_petrol_insufficient_balance_fail(self,
        balance,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory, balance=balance)

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert_error(response, status.HTTP_404_NOT_FOUND, "not_enough_balance")
        car.refresh_from_db()
        assert CarOperation.objects.count() == 0
        assert car.is_blocked_balance_update is False
        assert car.balance == balance


    def test_verify_driver_daily_fueling_limit_reached_fail(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        car_operation_factory,
        service,
    ):
        car = verifiable_car(car_factory, number_of_fuelings_per_day=1)
        car_operation_factory(
            car=car,
            driver=company_driver,
            service=service,
            status=CarOperation.OperationStatus.COMPLETED,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert_error(response, status.HTTP_400_BAD_REQUEST, "car_in_progress")
        car.refresh_from_db()
        assert CarOperation.objects.filter(car=car).count() == 1
        assert car.is_blocked_balance_update is False


    def test_verify_driver_daily_diesel_operations_count_toward_limit_fail(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        car_operation_factory,
        admin_user,
    ):
        diesel_service = Service.objects.create(
            name="Diesel 80",
            unit=Service.ServiceUnit.LITRE,
            type=Service.ServiceType.DIESEL,
            cost=Decimal("12.00"),
            created_by=admin_user,
        )
        car = verifiable_car(car_factory, number_of_fuelings_per_day=1)
        car_operation_factory(
            car=car,
            driver=company_driver,
            service=diesel_service,
            status=CarOperation.OperationStatus.COMPLETED,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert_error(response, status.HTTP_400_BAD_REQUEST, "car_in_progress")
        assert CarOperation.objects.filter(car=car).count() == 1


    def test_verify_driver_wash_operations_do_not_count_toward_fuel_limit_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        car_operation_factory,
        other_service,
    ):
        car = verifiable_car(car_factory, number_of_fuelings_per_day=1)
        car_operation_factory(
            car=car,
            driver=company_driver,
            service=other_service,
            status=CarOperation.OperationStatus.COMPLETED,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert CarOperation.objects.filter(car=car).count() == 2


    def test_verify_driver_yesterday_completed_fueling_does_not_block_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        car_operation_factory,
        service,
    ):
        car = verifiable_car(car_factory, number_of_fuelings_per_day=1)
        operation = car_operation_factory(
            car=car,
            driver=company_driver,
            service=service,
            status=CarOperation.OperationStatus.COMPLETED,
        )
        CarOperation.objects.filter(pk=operation.pk).update(
            created=timezone.localtime() - timedelta(days=1)
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert CarOperation.objects.filter(car=car).count() == 2


    def test_verify_driver_under_daily_fueling_limit_success(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
        car_operation_factory,
        service,
    ):
        car = verifiable_car(car_factory, number_of_fuelings_per_day=2)
        car_operation_factory(
            car=car,
            driver=company_driver,
            service=service,
            status=CarOperation.OperationStatus.COMPLETED,
        )

        response = worker_client(auth_client, station_worker, station).post(
            verify_url(company_driver.code, car.code)
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert CarOperation.objects.filter(car=car).count() == 2


    def test_verify_driver_second_request_blocked_after_success_fail(self,
        auth_client,
        station_worker,
        station,
        company_driver,
        car_factory,
    ):
        car = verifiable_car(car_factory)
        client = worker_client(auth_client, station_worker, station)

        first = client.post(verify_url(company_driver.code, car.code))
        second = client.post(verify_url(company_driver.code, car.code))

        assert first.status_code == status.HTTP_200_OK, first.data
        assert_error(second, status.HTTP_400_BAD_REQUEST, "car_in_progress")
        assert CarOperation.objects.filter(car=car).count() == 1
