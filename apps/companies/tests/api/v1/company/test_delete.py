import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Company

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def company_detail_url(company_id):
    return reverse("companies-detail", kwargs={"pk": company_id})


class TestCompanyDelete:

    def test_delete_without_authentication_fail(self, api_client, company):
        response = api_client.delete(company_detail_url(company.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Company.objects.filter(pk=company.id).exists()

    def test_delete_company_success(self, auth_client, admin_user, company_factory):
        target = company_factory()

        response = auth_client(admin_user).delete(company_detail_url(target.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.objects.filter(pk=target.id).exists()

    def test_delete_other_company_as_company_owner_success(
        self,
        auth_client,
        company_owner,
        company,
        company_factory,
    ):
        target = company_factory()

        response = auth_client(company_owner, company_id=company.id).delete(
            company_detail_url(target.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.objects.filter(pk=target.id).exists()

    @pytest.mark.parametrize("related_fixture", ["company_branch", "company_owner"])
    def test_delete_company_with_related_records_fail(
        self,
        related_fixture,
        request,
        auth_client,
        admin_user,
        company,
    ):
        request.getfixturevalue(related_fixture)
        client = auth_client(admin_user)
        client.raise_request_exception = False

        try:
            response = client.delete(company_detail_url(company.id))
        except Exception:
            response = None

        assert Company.objects.filter(pk=company.id).exists()
        if response is not None:
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_delete_unknown_company_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).delete(company_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
