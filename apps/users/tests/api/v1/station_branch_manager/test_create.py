import pytest
from rest_framework import status

from apps.users.models import StationBranchManager, StationOwner, User
from apps.users.tests.helpers import station_branch_managers_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_create_without_authentication_fail(
    api_client, station_branch_manager_payload_factory
):
    response = api_client.post(
        station_branch_managers_list_url(),
        station_branch_manager_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_as_company_owner_fail(
    auth_client, company_owner, company, station_branch_manager_payload_factory
):
    before = StationOwner.objects.filter(
        role=User.UserRoles.StationBranchManager
    ).count()

    response = auth_client(company_owner, company_id=company.id).post(
        station_branch_managers_list_url(),
        station_branch_manager_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert (
        StationOwner.objects.filter(role=User.UserRoles.StationBranchManager).count()
        == before
    )


def test_create_as_dashboard_success(
    auth_client, admin_user, station, branch, station_branch_manager_payload_factory
):
    payload = station_branch_manager_payload_factory()

    response = auth_client(admin_user).post(
        station_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = StationOwner.objects.get(phone_number=payload["phone_number"])
    assert created.role == User.UserRoles.StationBranchManager
    assert created.station_id == station.id
    assert created.check_password("password123")
    assert StationBranchManager.objects.filter(
        user=created, station_branch=branch
    ).exists()


def test_create_as_station_owner_uses_jwt_station_success(
    auth_client, station_owner, station, branch, station_branch_manager_payload_factory
):
    payload = station_branch_manager_payload_factory()
    payload.pop("station_id")

    response = auth_client(station_owner, station_id=station.id).post(
        station_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = StationOwner.objects.get(phone_number=payload["phone_number"])
    assert created.station_id == station.id


def test_create_dashboard_without_station_id_fail(
    auth_client, admin_user, station_branch_manager_payload_factory
):
    payload = station_branch_manager_payload_factory()
    payload.pop("station_id")
    before = StationOwner.objects.filter(
        role=User.UserRoles.StationBranchManager
    ).count()

    response = auth_client(admin_user).post(
        station_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        StationOwner.objects.filter(role=User.UserRoles.StationBranchManager).count()
        == before
    )


def test_create_password_mismatch_fail(
    auth_client, admin_user, station_branch_manager_payload_factory
):
    payload = station_branch_manager_payload_factory(confirm_password="other-pass")

    response = auth_client(admin_user).post(
        station_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_create_foreign_station_branches_fail(
    auth_client,
    admin_user,
    station,
    other_station_branch,
    station_branch_manager_payload_factory,
):
    payload = station_branch_manager_payload_factory(
        station_id=station.id,
        station_branches=[other_station_branch.id],
    )

    response = auth_client(admin_user).post(
        station_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
