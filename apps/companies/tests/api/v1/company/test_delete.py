import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Car, Company, CompanyBranch, Driver
from apps.companies.models.operation_model import CarOperation
from apps.users.models import CompanyBranchManager, CompanyUser
from apps.utilities.testing import assert_soft_deleted, listed_ids

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

    def test_delete_unknown_company_fail(self):
        response = self.client.delete(company_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCompanySoftDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, company):
        self.client = auth_client(admin_user)
        self.company = company
        response = self.client.delete(company_detail_url(company.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(Company, self.company.id)

    def test_deleted_company_hidden_from_list_success(self, other_company):
        response = self.client.get(reverse("companies-list"))

        assert response.status_code == status.HTTP_200_OK
        ids = listed_ids(response)
        assert self.company.id not in ids
        assert other_company.id in ids

    def test_retrieve_deleted_company_not_found_fail(self):
        response = self.client.get(company_detail_url(self.company.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_company_not_found_fail(self):
        response = self.client.delete(company_detail_url(self.company.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_company_with_deleted_company_name_success(
        self, company_payload_factory
    ):
        """Company has no unique fields, so the old values can be reused."""
        response = self.client.post(
            reverse("companies-list"),
            company_payload_factory(name=self.company.name),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Company.all_objects.filter(name=self.company.name).count() == 2


class TestCompanyCascadeSoftDelete:
    """Deleting a company soft deletes everything that belongs to it."""

    @pytest.fixture(autouse=True)
    def setup(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_owner,
        company_branch_manager,
        company_car,
        company_driver,
        cash_request_factory,
        company_transaction_factory,
    ):
        self.client = auth_client(admin_user)
        self.company = company
        self.owner = company_owner
        self.manager = company_branch_manager
        self.related = [
            (CompanyBranch, company_branch.id),
            (Car, company_car.id),
            (Driver, company_driver.id),
            (
                CompanyBranchManager,
                CompanyBranchManager.objects.get(company_branch=company_branch).id,
            ),
            (
                CompanyCashRequest,
                cash_request_factory(company=company, driver=company_driver).id,
            ),
            (CompanyKhaznaTransaction, company_transaction_factory().id),
        ]
        self.url = company_detail_url(company.id)

    def test_delete_company_soft_deletes_related_rows_success(self):
        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        company = assert_soft_deleted(Company, self.company.id)
        for model, pk in self.related:
            assert assert_soft_deleted(model, pk).deleted_at == company.deleted_at

    def test_delete_company_deactivates_owners_and_managers_success(self):
        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CompanyUser.objects.filter(
            pk__in=[self.owner.id, self.manager.id], is_active=True
        ).exists()

    def test_deactivated_company_owner_cannot_use_api_fail(self, auth_client):
        owner_client = auth_client(self.owner, company_id=self.company.id)

        self.client.delete(self.url)
        response = owner_client.get(reverse("cars-list"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_company_hides_related_rows_from_lists_success(self):
        self.client.delete(self.url)

        for list_name, model in [
            ("company-branches-list", CompanyBranch),
            ("cars-list", Car),
            ("drivers-list", Driver),
        ]:
            response = self.client.get(reverse(list_name))
            assert response.status_code == status.HTTP_200_OK
            pk = next(pk for related, pk in self.related if related is model)
            assert pk not in listed_ids(response)

    def test_delete_company_keeps_other_company_rows_success(
        self,
        other_company,
        other_company_branch,
        car_factory,
        driver_factory,
        other_company_owner,
    ):
        other_car = car_factory(branch=other_company_branch)
        other_driver = driver_factory(branch=other_company_branch)

        self.client.delete(self.url)

        assert Company.objects.filter(pk=other_company.id).exists()
        assert CompanyBranch.objects.filter(pk=other_company_branch.id).exists()
        assert Car.objects.filter(pk=other_car.id).exists()
        assert Driver.objects.filter(pk=other_driver.id).exists()
        assert CompanyUser.objects.filter(
            pk=other_company_owner.id, is_active=True
        ).exists()

    def test_delete_company_keeps_earlier_deleted_at_success(self):
        driver_id = next(pk for model, pk in self.related if model is Driver)
        Driver.objects.get(pk=driver_id).delete()
        earlier = Driver.all_objects.get(pk=driver_id).deleted_at

        self.client.delete(self.url)

        assert Driver.all_objects.get(pk=driver_id).deleted_at == earlier

    def test_queryset_delete_cascades_success(self):
        Company.objects.filter(pk=self.company.id).delete()

        assert_soft_deleted(Company, self.company.id)
        for model, pk in self.related:
            assert_soft_deleted(model, pk)

    def test_delete_company_with_operations_keeps_related_rows_fail(
        self, car_operation_factory
    ):
        car_operation_factory()

        response = self.client.delete(self.url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        for model, pk in self.related:
            assert model.objects.filter(pk=pk).exists()
