import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Car, CompanyBranch, Driver
from apps.users.models import User
from apps.utilities.testing import assert_soft_deleted, listed_ids

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def branch_detail_url(branch_id):
    return reverse("company-branches-detail", kwargs={"pk": branch_id})


class TestCompanyBranchDelete:

    def test_delete_without_authentication_fail(self, api_client, company_branch):
        response = api_client.delete(branch_detail_url(company_branch.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CompanyBranch.objects.filter(pk=company_branch.id).exists()

    def test_delete_branch_success(
        self, auth_client, admin_user, company_branch_factory
    ):
        target = company_branch_factory()

        response = auth_client(admin_user).delete(branch_detail_url(target.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CompanyBranch.objects.filter(pk=target.id).exists()

    def test_delete_owned_branch_as_company_owner_success(
        self, auth_client, company_owner, company, company_branch_factory
    ):
        target = company_branch_factory()

        response = auth_client(company_owner, company_id=company.id).delete(
            branch_detail_url(target.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CompanyBranch.objects.filter(pk=target.id).exists()

    def test_delete_other_company_branch_as_owner_fail(
        self, auth_client, company_owner, company, other_company_branch
    ):
        response = auth_client(company_owner, company_id=company.id).delete(
            branch_detail_url(other_company_branch.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert CompanyBranch.objects.filter(pk=other_company_branch.id).exists()

    def test_delete_unmanaged_branch_as_branch_manager_fail(
        self, auth_client, company_branch_manager, company, second_company_branch
    ):
        response = auth_client(company_branch_manager, company_id=company.id).delete(
            branch_detail_url(second_company_branch.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert CompanyBranch.objects.filter(pk=second_company_branch.id).exists()

    @pytest.mark.parametrize(
        ("related_fixture", "related_model"),
        [
            ("company_car", Car),
            ("company_driver", Driver),
            ("company_branch_manager", User),
        ],
    )
    def test_delete_branch_with_related_records_keeps_them_success(
        self,
        related_fixture,
        related_model,
        request,
        auth_client,
        admin_user,
        company_branch,
    ):
        """Soft delete skips `on_delete=PROTECT`: related rows stay active."""
        related = request.getfixturevalue(related_fixture)

        response = auth_client(admin_user).delete(branch_detail_url(company_branch.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert_soft_deleted(CompanyBranch, company_branch.id)
        assert related_model.objects.filter(pk=related.id).exists()

    def test_delete_unknown_branch_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).delete(branch_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCompanyBranchSoftDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, company_branch_factory):
        self.client = auth_client(admin_user)
        self.branch = company_branch_factory()
        response = self.client.delete(branch_detail_url(self.branch.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(CompanyBranch, self.branch.id)

    def test_deleted_branch_hidden_from_list_success(self, company_branch):
        response = self.client.get(reverse("company-branches-list"))

        assert response.status_code == status.HTTP_200_OK
        ids = listed_ids(response)
        assert self.branch.id not in ids
        assert company_branch.id in ids

    def test_retrieve_deleted_branch_not_found_fail(self):
        response = self.client.get(branch_detail_url(self.branch.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_branch_not_found_fail(self):
        response = self.client.delete(branch_detail_url(self.branch.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_branch_with_deleted_branch_values_success(
        self, company_branch_payload_factory
    ):
        """CompanyBranch has no unique fields, so old values can be reused."""
        response = self.client.post(
            reverse("company-branches-list"),
            company_branch_payload_factory(
                name=self.branch.name,
                email=self.branch.email,
                phone_number=self.branch.phone_number,
            ),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert CompanyBranch.all_objects.filter(name=self.branch.name).count() == 2
