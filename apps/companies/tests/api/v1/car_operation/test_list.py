from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import (
    assert_operation_payload,
    operation_list_url,
    returned_ids,
)
from apps.stations.models.service_models import Service


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_list_without_authentication_fail(api_client):
    response = api_client.get(operation_list_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_list_company_owner_petrol_scope_success(
    auth_client,
    company_owner,
    company,
    car_factory,
    driver_factory,
    other_company_branch,
    other_service,
    car_operation_factory,
):
    petrol = car_operation_factory()
    wash = car_operation_factory(service=other_service, unit=Service.ServiceUnit.UNIT)
    other_company = car_operation_factory(
        car=car_factory(branch=other_company_branch),
        driver=driver_factory(branch=other_company_branch),
    )

    response = auth_client(company_owner, company_id=company.id).get(
        operation_list_url()
    )

    assert response.status_code == status.HTTP_200_OK
    assert petrol.id in returned_ids(response)
    assert wash.id not in returned_ids(response)
    assert other_company.id not in returned_ids(response)
    item = next(row for row in response.data["results"] if row["id"] == petrol.id)
    assert_operation_payload(item, petrol, company_owner, include_profits=False)
    assert item["service_category"] == "خدمات بترولية"
    assert item["unit"] == "لتر"
    assert item["duration"] == 2
    assert item["amount"] == "10.00"
    assert item["company_cost"] == "100.00"
    assert item["station_cost"] == "100.00"
    assert item["cost"] == "100.00"
    assert "profits" not in item


def test_list_branch_manager_managed_branch_scope_success(
    auth_client,
    company_branch_manager,
    company,
    car_factory,
    driver_factory,
    second_company_branch,
    car_operation_factory,
):
    managed = car_operation_factory()
    unmanaged = car_operation_factory(
        car=car_factory(branch=second_company_branch),
        driver=driver_factory(branch=second_company_branch),
    )

    response = auth_client(company_branch_manager, company_id=company.id).get(
        operation_list_url()
    )

    assert response.status_code == status.HTTP_200_OK
    assert managed.id in returned_ids(response)
    assert unmanaged.id not in returned_ids(response)
    item = next(row for row in response.data["results"] if row["id"] == managed.id)
    assert_operation_payload(
        item, managed, company_branch_manager, include_profits=False
    )


def test_list_dashboard_and_station_see_all_including_wash_success(
    auth_client,
    admin_user,
    station_worker,
    station,
    other_service,
    other_company_branch,
    car_factory,
    driver_factory,
    car_operation_factory,
):
    petrol = car_operation_factory()
    wash = car_operation_factory(service=other_service, unit=Service.ServiceUnit.UNIT)
    other_company = car_operation_factory(
        car=car_factory(branch=other_company_branch),
        driver=driver_factory(branch=other_company_branch),
    )

    admin_response = auth_client(admin_user).get(operation_list_url())
    worker_response = auth_client(station_worker, station_id=station.id).get(
        operation_list_url()
    )

    assert admin_response.status_code == status.HTTP_200_OK
    assert worker_response.status_code == status.HTTP_200_OK
    expected_ids = {petrol.id, wash.id, other_company.id}
    assert expected_ids.issubset(returned_ids(admin_response))
    assert expected_ids.issubset(returned_ids(worker_response))
    admin_item = next(
        row for row in admin_response.data["results"] if row["id"] == petrol.id
    )
    assert_operation_payload(admin_item, petrol, admin_user, include_profits=True)
    assert admin_item["profits"] == "0.00"
    wash_item = next(
        row for row in worker_response.data["results"] if row["id"] == wash.id
    )
    assert_operation_payload(wash_item, wash, station_worker, include_profits=True)
    assert wash_item["service_category"] == "خدمات أخرى"
    assert wash_item["unit"] == "وحدة"


@pytest.mark.parametrize("role_fixture", ["station_owner", "branch_manager"])
def test_list_station_admin_roles_success(
    role_fixture,
    request,
    auth_client,
    station,
    car_operation_factory,
):
    user = request.getfixturevalue(role_fixture)
    operation = car_operation_factory()

    response = auth_client(user, station_id=station.id).get(operation_list_url())

    assert response.status_code == status.HTTP_200_OK
    assert operation.id in returned_ids(response)
    item = next(row for row in response.data["results"] if row["id"] == operation.id)
    assert_operation_payload(item, operation, user, include_profits=True)


def test_list_filter_status_and_car_success(
    auth_client,
    company_owner,
    company,
    car_factory,
    driver_factory,
    car_operation_factory,
):
    pending = car_operation_factory(status=CarOperation.OperationStatus.PENDING)
    completed = car_operation_factory(
        status=CarOperation.OperationStatus.COMPLETED,
        car=car_factory(),
        driver=driver_factory(),
    )

    by_status = auth_client(company_owner, company_id=company.id).get(
        operation_list_url(),
        {"status": "pending,cancelled"},
    )
    by_car = auth_client(company_owner, company_id=company.id).get(
        operation_list_url(),
        {"car": pending.car_id},
    )

    assert by_status.status_code == status.HTTP_200_OK
    assert pending.id in returned_ids(by_status)
    assert completed.id not in returned_ids(by_status)
    assert by_car.status_code == status.HTTP_200_OK
    assert returned_ids(by_car) == {pending.id}


def test_list_filter_station_driver_worker_service_success(
    auth_client,
    admin_user,
    company_driver,
    station_worker,
    station,
    branch,
    service,
    other_service,
    car_operation_factory,
):
    matching = car_operation_factory()
    other = car_operation_factory(
        service=other_service,
        unit=Service.ServiceUnit.UNIT,
        driver=company_driver,
    )

    response = auth_client(admin_user).get(
        operation_list_url(),
        {
            "station": station.id,
            "station_branch": branch.id,
            "driver": company_driver.id,
            "worker": station_worker.id,
            "service": service.id,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert matching.id in returned_ids(response)
    assert other.id not in returned_ids(response)


def test_list_filter_start_and_end_date_success(
    auth_client,
    company_owner,
    company,
    car_operation_factory,
):
    today = timezone.localdate()
    matching = car_operation_factory(
        start_time=timezone.now(),
        end_time=timezone.now(),
    )

    response = auth_client(company_owner, company_id=company.id).get(
        operation_list_url(),
        {
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert matching.id in returned_ids(response)


def test_list_search_code_success(
    auth_client,
    company_owner,
    company,
    car_operation_factory,
):
    matching = car_operation_factory(code="SEARCHOP01")
    other = car_operation_factory(code="OTHEROP001")

    response = auth_client(company_owner, company_id=company.id).get(
        operation_list_url(),
        {"search": "SEARCHOP01"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert returned_ids(response) == {matching.id}
    assert other.id not in returned_ids(response)
    assert_operation_payload(
        response.data["results"][0], matching, company_owner, include_profits=False
    )


def test_list_without_pagination_success(
    auth_client,
    company_owner,
    company,
    car_operation_factory,
):
    operation = car_operation_factory()

    response = auth_client(company_owner, company_id=company.id).get(
        operation_list_url(),
        {"no_paginate": "true"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert "count" not in response.data
    assert [item["id"] for item in response.data["results"]] == [operation.id]
    assert_operation_payload(
        response.data["results"][0], operation, company_owner, include_profits=False
    )
