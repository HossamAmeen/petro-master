import pytest
from rest_framework import status

from apps.users.models import CompanyUser, User
from apps.users.tests.helpers import company_branch_managers_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_create_without_authentication_fail(
    api_client, company_branch_manager_payload_factory
):
    response = api_client.post(
        company_branch_managers_list_url(),
        company_branch_manager_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_create_as_station_owner_fail(
    auth_client, station_owner, station, company_branch_manager_payload_factory
):
    before = CompanyUser.objects.count()

    response = auth_client(station_owner, station_id=station.id).post(
        company_branch_managers_list_url(),
        company_branch_manager_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert CompanyUser.objects.count() == before


def test_create_as_dashboard_success(
    auth_client, admin_user, company, company_branch_manager_payload_factory
):
    payload = company_branch_manager_payload_factory()
    payload.pop("company_branches")

    response = auth_client(admin_user).post(
        company_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyUser.objects.get(phone_number=payload["phone_number"])
    assert created.company_id == company.id
    assert created.check_password("password123")
    # create action uses CreateCompanyOwnerSerializer
    assert created.role == User.UserRoles.CompanyOwner


def test_create_as_company_owner_success(
    auth_client, company_owner, company, company_branch_manager_payload_factory
):
    payload = company_branch_manager_payload_factory()
    payload.pop("company_branches")

    response = auth_client(company_owner, company_id=company.id).post(
        company_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyUser.objects.get(phone_number=payload["phone_number"])
    assert created.company_id == company.id
    assert created.role == User.UserRoles.CompanyOwner


def test_create_dashboard_without_company_id_fail(
    auth_client, admin_user, company_branch_manager_payload_factory
):
    payload = company_branch_manager_payload_factory()
    payload.pop("company_id")
    payload.pop("company_branches")
    before = CompanyUser.objects.count()

    response = auth_client(admin_user).post(
        company_branch_managers_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CompanyUser.objects.count() == before
