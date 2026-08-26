import pytest
from rest_framework import status

from apps.companies.tests.api.v1.car_operation.helpers import (
    assert_operation_payload,
    operation_detail_url,
)
from apps.stations.models.service_models import Service


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_retrieve_without_authentication_fail(api_client, car_operation_factory):
    operation = car_operation_factory()

    response = api_client.get(operation_detail_url(operation.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_as_company_owner_success(
    auth_client, company_owner, company, car_operation_factory
):
    operation = car_operation_factory()

    response = auth_client(company_owner, company_id=company.id).get(
        operation_detail_url(operation.id)
    )

    assert response.status_code == status.HTTP_200_OK
    assert_operation_payload(response.data, operation, include_profits=True)
    assert response.data["id"] == operation.id
    assert response.data["code"] == operation.code
    assert response.data["status"] == operation.status
    assert response.data["car"]["id"] == operation.car_id
    assert response.data["car"]["code"] == operation.car.code
    assert response.data["car"]["plate_number"] == operation.car.plate_number
    assert response.data["car"]["plate_character"] == operation.car.plate_character
    assert response.data["car"]["plate_color"] == operation.car.plate_color
    assert response.data["driver"]["id"] == operation.driver_id
    assert response.data["driver"]["name"] == operation.driver.name
    assert response.data["driver"]["phone_number"] == operation.driver.phone_number
    assert response.data["driver"]["branch"] == operation.driver.branch_id
    assert response.data["driver"]["code"] == operation.driver.code
    assert response.data["station_branch"]["id"] == operation.station_branch_id
    assert response.data["station_branch"]["name"] == operation.station_branch.name
    assert response.data["station_branch"]["address"] == operation.station_branch.address
    assert response.data["station_branch"]["district"] == (
        operation.station_branch.district_id
    )
    assert response.data["station_branch"]["station"] == (
        operation.station_branch.station_id
    )
    assert response.data["worker"]["id"] == operation.worker_id
    assert response.data["worker"]["name"] == operation.worker.name
    assert response.data["worker"]["phone_number"] == operation.worker.phone_number
    assert response.data["worker"]["station_branch"]["id"] == (
        operation.worker.station_branch_id
    )
    assert response.data["service"] == {
        "id": operation.service_id,
        "name": operation.service.name,
    }
    assert response.data["amount"] == "10.00"
    assert response.data["cost"] == "100.00"
    assert response.data["company_cost"] == "100.00"
    assert response.data["station_cost"] == "100.00"
    assert response.data["profits"] == "0.00"
    assert response.data["unit"] == "لتر"
    assert response.data["duration"] == 2
    assert response.data["service_category"] == "خدمات بترولية"
    assert response.data["fuel_type"] == operation.fuel_type
    assert response.data["car_meter"] == "10000.00"
    assert response.data["motor_image"] in (None, "")
    assert response.data["fuel_image"] in (None, "")


def test_retrieve_wash_as_company_owner_fail(
    auth_client, company_owner, company, other_service, car_operation_factory
):
    operation = car_operation_factory(
        service=other_service, unit=Service.ServiceUnit.UNIT
    )

    response = auth_client(company_owner, company_id=company.id).get(
        operation_detail_url(operation.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_unmanaged_branch_as_manager_fail(
    auth_client,
    company_branch_manager,
    company,
    car_factory,
    driver_factory,
    second_company_branch,
    car_operation_factory,
):
    operation = car_operation_factory(
        car=car_factory(branch=second_company_branch),
        driver=driver_factory(branch=second_company_branch),
    )

    response = auth_client(company_branch_manager, company_id=company.id).get(
        operation_detail_url(operation.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_other_company_as_owner_fail(
    auth_client,
    company_owner,
    company,
    car_factory,
    driver_factory,
    other_company_branch,
    car_operation_factory,
):
    operation = car_operation_factory(
        car=car_factory(branch=other_company_branch),
        driver=driver_factory(branch=other_company_branch),
    )

    response = auth_client(company_owner, company_id=company.id).get(
        operation_detail_url(operation.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_as_station_worker_success(
    auth_client, station_worker, station, other_service, car_operation_factory
):
    operation = car_operation_factory(
        service=other_service, unit=Service.ServiceUnit.UNIT
    )

    response = auth_client(station_worker, station_id=station.id).get(
        operation_detail_url(operation.id)
    )

    assert response.status_code == status.HTTP_200_OK
    assert_operation_payload(response.data, operation, include_profits=True)
    assert response.data["service_category"] == "خدمات أخرى"
    assert response.data["unit"] == "وحدة"


def test_retrieve_unknown_operation_fail(auth_client, company_owner, company):
    response = auth_client(company_owner, company_id=company.id).get(
        operation_detail_url(999_999)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
