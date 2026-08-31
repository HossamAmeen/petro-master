import pytest
from rest_framework import status

from apps.users.models import CompanyUser
from apps.users.tests.helpers import company_owners_detail_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyOwnerDelete:


    def test_delete_without_authentication_fail(self, api_client, company_owner):
        response = api_client.delete(company_owners_detail_url(company_owner.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CompanyUser.objects.filter(pk=company_owner.id).exists()


    def test_delete_as_company_owner_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).delete(
            company_owners_detail_url(company_owner.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CompanyUser.objects.filter(pk=company_owner.id).exists()


    def test_delete_success(self, auth_client, admin_user, other_company_owner):
        user_id = other_company_owner.id

        response = auth_client(admin_user).delete(company_owners_detail_url(user_id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CompanyUser.objects.filter(pk=user_id).exists()


    def test_delete_unknown_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).delete(company_owners_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
