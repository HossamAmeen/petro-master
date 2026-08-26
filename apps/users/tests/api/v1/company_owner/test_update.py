import pytest
from rest_framework import status

from apps.users.tests.helpers import company_owners_detail_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_update_without_authentication_fail(api_client, company_owner):
    response = api_client.patch(
        company_owners_detail_url(company_owner.id),
        {"name": "Hacker"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_update_as_station_owner_fail(auth_client, station_owner, station, company_owner):
    response = auth_client(station_owner, station_id=station.id).patch(
        company_owners_detail_url(company_owner.id),
        {"name": "Nope"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    company_owner.refresh_from_db()
    assert company_owner.name != "Nope"


def test_update_name_success(auth_client, admin_user, company_owner, company):
    response = auth_client(admin_user).patch(
        company_owners_detail_url(company_owner.id),
        {"name": "Updated Owner", "company_id": company.id},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    company_owner.refresh_from_db()
    assert company_owner.name == "Updated Owner"


def test_update_password_success(auth_client, admin_user, company_owner, company):
    response = auth_client(admin_user).patch(
        company_owners_detail_url(company_owner.id),
        {"password": "new-owner-pass", "company_id": company.id},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    company_owner.refresh_from_db()
    assert company_owner.check_password("new-owner-pass")
