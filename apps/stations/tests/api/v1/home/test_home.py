from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.stations.tests.helpers import home_url, set_balance


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_home_without_authentication_fail(api_client):
    response = api_client.get(home_url())

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "role_fixture",
    ["admin_user", "finance_user", "company_owner", "company_branch_manager"],
)
def test_home_forbidden_role_fail(
    role_fixture, request, auth_client, company, station
):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {"company_id": company.id} if "company" in role_fixture else {}

    response = auth_client(user, **client_kwargs).get(home_url())

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_home_post_not_allowed_fail(auth_client, station_owner, station):
    response = auth_client(station_owner, station_id=station.id).post(home_url())

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_home_owner_balances_and_counts_success(
    auth_client,
    station_owner,
    station,
    branch,
    second_station_branch,
    station_worker,
    branch_manager,
    gas_operation,
):
    set_balance(station, "80.00")
    set_balance(branch, "30.00")
    set_balance(second_station_branch, "20.00")

    response = auth_client(station_owner, station_id=station.id).get(home_url())

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == station.id
    assert response.data["name"] == station.name
    assert response.data["station_name"] == station.name
    assert response.data["user_name"] == station_owner.name
    assert response.data["address"] == station.address
    assert response.data["station_branch_id"] is None
    assert Decimal(str(response.data["balance"])) == Decimal("80.00")
    assert Decimal(str(response.data["branches_balance"])) == Decimal("50.00")
    assert Decimal(str(response.data["distributed_balance"])) == Decimal("50.00")
    assert Decimal(str(response.data["total_balance"])) == Decimal("130.00")
    assert response.data["branches_count"] == 2
    assert response.data["workers_count"] == 1
    assert response.data["managers_count"] == 1
    assert len(response.data["last_operations"]) >= 1
    assert response.data["last_operations"][0]["id"] == gas_operation.id


def test_home_branch_manager_scoped_success(
    auth_client,
    branch_manager,
    station,
    branch,
    second_station_branch,
    station_worker,
    second_station_worker,
    gas_operation,
    car_operation_factory,
):
    set_balance(branch, "40.00")
    set_balance(second_station_branch, "90.00")
    other_op = car_operation_factory(station_branch=second_station_branch)

    response = auth_client(branch_manager, station_id=station.id).get(home_url())

    assert response.status_code == status.HTTP_200_OK
    assert Decimal(str(response.data["balance"])) == Decimal("40.00")
    assert Decimal(str(response.data["distributed_balance"])) == Decimal("40.00")
    assert Decimal(str(response.data["total_balance"])) == Decimal("80.00")
    assert response.data["branches_count"] == 1
    assert response.data["workers_count"] == 1
    assert response.data["managers_count"] == 0
    last_ids = {item["id"] for item in response.data["last_operations"]}
    assert gas_operation.id in last_ids
    assert other_op.id not in last_ids


def test_home_worker_zero_balances_success(
    auth_client, station_worker, station, branch, gas_operation
):
    set_balance(station, "80.00")
    set_balance(branch, "30.00")

    response = auth_client(station_worker, station_id=station.id).get(home_url())

    assert response.status_code == status.HTTP_200_OK
    assert response.data["station_branch_id"] == branch.id
    assert response.data["balance"] == 0
    assert response.data["branches_balance"] == 0
    assert response.data["distributed_balance"] == 0
    assert response.data["total_balance"] == 0
    assert response.data["workers_count"] == 0
    assert response.data["managers_count"] == 0
    assert response.data["branches_count"] == 0
    last_ids = {item["id"] for item in response.data["last_operations"]}
    assert gas_operation.id in last_ids
