import math
from decimal import Decimal

from django.urls import reverse
from rest_framework.fields import DateTimeField

from apps.companies.tests.helpers import set_balance  # noqa: F401  (re-exported)
from apps.shared.constants import COMPANY_ROLES, SERVICE_UNIT_CHOICES
from apps.stations.models.service_models import Service


def operation_list_url():
    return reverse("car-operations-list")


def operation_detail_url(operation_id):
    return reverse("car-operations-detail", kwargs={"pk": operation_id})


def operation_export_url():
    return reverse("car-operations-export")


def operation_download_url():
    return reverse("car-operations-download-excel")


def returned_ids(response):
    return {item["id"] for item in response.data["results"]}


def expected_service_category(operation):
    if operation.service and operation.service.type in [
        Service.ServiceType.PETROL,
        Service.ServiceType.DIESEL,
    ]:
        return "خدمات بترولية"
    return "خدمات أخرى"


def expected_car_payload(car):
    return {
        "id": car.id,
        "code": car.code,
        "plate_number": car.plate_number,
        "plate_character": car.plate_character,
        "plate_color": car.plate_color,
    }


def expected_driver_payload(driver):
    return {
        "id": driver.id,
        "name": driver.name,
        "phone_number": driver.phone_number,
        "branch": driver.branch_id,
        "code": driver.code,
    }


def expected_station_branch_payload(station_branch):
    return {
        "id": station_branch.id,
        "name": station_branch.name,
        "address": station_branch.address,
        "district": station_branch.district_id,
        "station": station_branch.station_id,
    }


def expected_worker_station_branch_payload(station_branch):
    return {
        "id": station_branch.id,
        "name": station_branch.name,
        "address": station_branch.address,
        "district": {
            "id": station_branch.district_id,
            "name": station_branch.district.name,
            "city": {"name": station_branch.district.city.name},
        },
        "station": station_branch.station_id,
    }


def expected_worker_payload(worker):
    return {
        "id": worker.id,
        "name": worker.name,
        "phone_number": worker.phone_number,
        "station_branch": expected_worker_station_branch_payload(worker.station_branch),
    }


def _as_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def _as_datetime(value):
    return DateTimeField().to_representation(value)


def assert_operation_payload(data, operation, user=None, *, include_profits=None):
    operation.refresh_from_db()
    if include_profits is None:
        include_profits = user is None or user.role not in COMPANY_ROLES

    assert data["id"] == operation.id
    assert data["code"] == operation.code
    assert data["status"] == operation.status
    assert data["start_time"] == _as_datetime(operation.start_time)
    assert data["end_time"] == _as_datetime(operation.end_time)
    assert data["created"] == _as_datetime(operation.created)
    assert data["duration"] == math.ceil(operation.duration / 60)
    assert _as_decimal(data["cost"]) == _as_decimal(operation.cost)
    assert _as_decimal(data["company_cost"]) == _as_decimal(operation.company_cost)
    assert _as_decimal(data["station_cost"]) == _as_decimal(operation.station_cost)
    assert _as_decimal(data["amount"]) == _as_decimal(operation.amount)
    assert data["unit"] == SERVICE_UNIT_CHOICES.get(operation.unit, operation.unit)
    assert data["fuel_type"] == operation.fuel_type
    assert data["car"] == expected_car_payload(operation.car)
    assert data["driver"] == expected_driver_payload(operation.driver)
    assert data["station_branch"] == expected_station_branch_payload(
        operation.station_branch
    )
    assert data["worker"] == expected_worker_payload(operation.worker)
    assert data["service"] == {
        "id": operation.service_id,
        "name": operation.service.name,
    }
    assert _as_decimal(data["car_meter"]) == _as_decimal(operation.car_meter)
    assert data["motor_image"] in (None, "")
    assert data["fuel_image"] in (None, "")
    assert _as_decimal(data["fuel_consumption_rate"]) == _as_decimal(
        operation.fuel_consumption_rate
    )
    assert data["service_category"] == expected_service_category(operation)
    if include_profits:
        assert _as_decimal(data["profits"]) == _as_decimal(operation.profits)
    else:
        assert "profits" not in data
