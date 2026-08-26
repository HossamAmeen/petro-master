import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import CompanyBranch


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def branch_detail_url(branch_id):
    return reverse("company-branches-detail", kwargs={"pk": branch_id})


def test_delete_without_authentication_fail(api_client, company_branch):
    response = api_client.delete(branch_detail_url(company_branch.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert CompanyBranch.objects.filter(pk=company_branch.id).exists()


def test_delete_branch_success(auth_client, admin_user, company_branch_factory):
    target = company_branch_factory()

    response = auth_client(admin_user).delete(branch_detail_url(target.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not CompanyBranch.objects.filter(pk=target.id).exists()


def test_delete_owned_branch_as_company_owner_success(
    auth_client, company_owner, company, company_branch_factory
):
    target = company_branch_factory()

    response = auth_client(company_owner, company_id=company.id).delete(
        branch_detail_url(target.id)
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not CompanyBranch.objects.filter(pk=target.id).exists()


def test_delete_other_company_branch_as_owner_fail(
    auth_client, company_owner, company, other_company_branch
):
    response = auth_client(company_owner, company_id=company.id).delete(
        branch_detail_url(other_company_branch.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert CompanyBranch.objects.filter(pk=other_company_branch.id).exists()


def test_delete_unmanaged_branch_as_branch_manager_fail(
    auth_client, company_branch_manager, company, second_company_branch
):
    response = auth_client(company_branch_manager, company_id=company.id).delete(
        branch_detail_url(second_company_branch.id)
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert CompanyBranch.objects.filter(pk=second_company_branch.id).exists()


@pytest.mark.parametrize("related_fixture", ["company_car", "company_driver", "company_branch_manager"])
def test_delete_branch_with_related_records_fail(
    related_fixture,
    request,
    auth_client,
    admin_user,
    company_branch,
):
    request.getfixturevalue(related_fixture)
    client = auth_client(admin_user)
    client.raise_request_exception = False

    try:
        response = client.delete(branch_detail_url(company_branch.id))
    except Exception:
        response = None

    assert CompanyBranch.objects.filter(pk=company_branch.id).exists()
    if response is not None:
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_delete_unknown_branch_fail(auth_client, admin_user):
    response = auth_client(admin_user).delete(branch_detail_url(999_999))

    assert response.status_code == status.HTTP_404_NOT_FOUND
