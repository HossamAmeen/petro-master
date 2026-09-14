import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Company
from apps.companies.models.operation_model import CarOperation

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def company_detail_url(company_id):
    return reverse("companies-detail", kwargs={"pk": company_id})


class TestCompanyDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, company):
        self.client = auth_client(admin_user)
        self.company = company
        self.url = company_detail_url(company.id)

    def test_delete_without_authentication_fail(self, api_client):
        response = api_client.delete(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Company.objects.filter(pk=self.company.id).exists()

    def test_delete_company_success(self):
        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.objects.filter(pk=self.company.id).exists()

    def test_delete_other_company_as_company_owner_success(
        self, auth_client, company_owner, company_factory
    ):
        target = company_factory()

        response = auth_client(company_owner, company_id=self.company.id).delete(
            company_detail_url(target.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.objects.filter(pk=target.id).exists()

    @pytest.mark.parametrize("operation_status", CarOperation.OperationStatus.values)
    def test_delete_company_with_operations_fail(
        self, operation_status, car_operation_factory
    ):
        operation = car_operation_factory(status=operation_status)

        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "has_operations"
        assert Company.objects.filter(pk=self.company.id).exists()
        assert CarOperation.objects.filter(pk=operation.id).exists()

    def test_delete_company_without_own_operations_success(
        self, car_operation_factory, other_company
    ):
        car_operation_factory()

        response = self.client.delete(company_detail_url(other_company.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Company.objects.filter(pk=other_company.id).exists()

    @pytest.mark.parametrize("related_fixture", ["company_branch", "company_owner"])
    def test_delete_company_with_related_records_fail(self, related_fixture, request):
        request.getfixturevalue(related_fixture)
        self.client.raise_request_exception = False

        try:
            response = self.client.delete(self.url)
        except Exception:
            response = None

        assert Company.objects.filter(pk=self.company.id).exists()
        if response is not None:
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_delete_unknown_company_fail(self):
        response = self.client.delete(company_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
