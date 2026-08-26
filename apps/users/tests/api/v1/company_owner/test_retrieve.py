import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import company_owners_detail_url, user_ref


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_retrieve_without_authentication_fail(api_client, company_owner):
    response = api_client.get(company_owners_detail_url(company_owner.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_retrieve_as_company_owner_fail(auth_client, company_owner, company):
    response = auth_client(company_owner, company_id=company.id).get(
        company_owners_detail_url(company_owner.id)
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_retrieve_success(auth_client, admin_user, company_owner, company):
    response = auth_client(admin_user).get(company_owners_detail_url(company_owner.id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == company_owner.id
    assert response.data["name"] == company_owner.name
    assert response.data["email"] == company_owner.email
    assert response.data["phone_number"] == company_owner.phone_number
    assert response.data["role"] == User.UserRoles.CompanyOwner
    assert response.data["company_id"] == company.id
    assert response.data["created_by"] == user_ref(admin_user)


def test_retrieve_branch_manager_fail(auth_client, admin_user, company_branch_manager):
    response = auth_client(admin_user).get(
        company_owners_detail_url(company_branch_manager.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_retrieve_unknown_fail(auth_client, admin_user):
    response = auth_client(admin_user).get(company_owners_detail_url(999_999))

    assert response.status_code == status.HTTP_404_NOT_FOUND
