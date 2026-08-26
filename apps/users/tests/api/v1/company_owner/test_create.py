import pytest
from rest_framework import status

from apps.users.models import CompanyUser, User
from apps.users.tests.helpers import company_owners_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyOwnerCreate:


    def test_create_without_authentication_fail(self,
        api_client, company_owner_payload_factory
    ):
        response = api_client.post(
            company_owners_list_url(),
            company_owner_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CompanyUser.objects.filter(role=User.UserRoles.CompanyOwner).count() == 0


    def test_create_as_company_owner_fail(self,
        auth_client, company_owner, company, company_owner_payload_factory
    ):
        before = CompanyUser.objects.count()

        response = auth_client(company_owner, company_id=company.id).post(
            company_owners_list_url(),
            company_owner_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CompanyUser.objects.count() == before


    def test_create_as_dashboard_success(self,
        auth_client, finance_user, company, company_owner_payload_factory
    ):
        payload = company_owner_payload_factory()

        response = auth_client(finance_user).post(
            company_owners_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CompanyUser.objects.get(phone_number=payload["phone_number"])
        assert created.role == User.UserRoles.CompanyOwner
        assert created.company_id == company.id
        assert created.check_password("password123")
        assert created.email == payload["email"]


    def test_create_defaults_email_success(self,
        auth_client, admin_user, company_owner_payload_factory
    ):
        payload = company_owner_payload_factory()
        payload.pop("email")

        response = auth_client(admin_user).post(
            company_owners_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CompanyUser.objects.get(phone_number=payload["phone_number"])
        assert created.email == f"{payload['phone_number']}@petro.com"


    def test_create_without_company_id_fail(self,
        auth_client, admin_user, company_owner_payload_factory
    ):
        payload = company_owner_payload_factory()
        payload.pop("company_id")
        before = CompanyUser.objects.count()

        response = auth_client(admin_user).post(
            company_owners_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CompanyUser.objects.count() == before


    def test_create_with_foreign_company_branches_fail(self,
        auth_client,
        admin_user,
        company,
        other_company_branch,
        company_owner_payload_factory,
    ):
        payload = company_owner_payload_factory(
            company_id=company.id,
            company_branches=[other_company_branch.id],
        )
        before = CompanyUser.objects.count()

        response = auth_client(admin_user).post(
            company_owners_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CompanyUser.objects.count() == before


    def test_create_missing_name_fail(self, auth_client, admin_user, company_owner_payload_factory):
        payload = company_owner_payload_factory()
        payload.pop("name")

        response = auth_client(admin_user).post(
            company_owners_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
