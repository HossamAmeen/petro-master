import pytest
from django.urls import reverse
from rest_framework import status

from apps.users.models import CompanyBranchManager


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def assign_managers_url(branch_id):
    return reverse("company-branches-assign-managers", kwargs={"pk": branch_id})


def assigned_user_ids(branch):
    return set(
        CompanyBranchManager.objects.filter(company_branch=branch).values_list(
            "user_id", flat=True
        )
    )


def test_assign_managers_without_authentication_fail(
    api_client, company_branch, company_branch_manager
):
    response = api_client.post(
        assign_managers_url(company_branch.id),
        {"managers": [company_branch_manager.id]},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "role_fixture",
    ["admin_user", "company_branch_manager", "station_worker"],
)
def test_assign_managers_forbidden_role_fail(
    role_fixture,
    request,
    auth_client,
    company,
    station,
    company_branch,
    branch_manager_user_factory,
):
    user = request.getfixturevalue(role_fixture)
    manager = branch_manager_user_factory()
    client_kwargs = {}
    if role_fixture == "company_branch_manager":
        client_kwargs["company_id"] = company.id
    if role_fixture == "station_worker":
        client_kwargs["station_id"] = station.id

    response = auth_client(user, **client_kwargs).post(
        assign_managers_url(company_branch.id),
        {"managers": [manager.id]},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_assign_managers_success(
    auth_client,
    company_owner,
    company,
    company_branch,
    company_branch_manager,
    branch_manager_user_factory,
):
    replacement = branch_manager_user_factory()

    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(company_branch.id),
        {"managers": [replacement.id]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data["message"] == "تم تعيين المديرين بنجاح"
    assert assigned_user_ids(company_branch) == {replacement.id}
    assert company_branch_manager.id not in assigned_user_ids(company_branch)


def test_assign_multiple_managers_success(
    auth_client,
    company_owner,
    company,
    company_branch,
    branch_manager_user_factory,
):
    first = branch_manager_user_factory()
    second = branch_manager_user_factory()

    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(company_branch.id),
        {"managers": [first.id, second.id, first.id]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert assigned_user_ids(company_branch) == {first.id, second.id}


def test_assign_managers_empty_list_fail(
    auth_client, company_owner, company, company_branch
):
    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(company_branch.id),
        {"managers": []},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert assigned_user_ids(company_branch) == set()


def test_assign_managers_missing_field_fail(
    auth_client, company_owner, company, company_branch
):
    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(company_branch.id),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_assign_managers_owner_is_invalid_fail(
    auth_client, company_owner, company, company_branch
):
    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(company_branch.id),
        {"managers": [company_owner.id]},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert assigned_user_ids(company_branch) == set()


def test_assign_managers_other_company_manager_fail(
    auth_client,
    company_owner,
    company,
    other_company,
    company_branch,
    branch_manager_user_factory,
):
    other_manager = branch_manager_user_factory(company=other_company)

    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(company_branch.id),
        {"managers": [other_manager.id]},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert assigned_user_ids(company_branch) == set()


def test_assign_managers_unknown_user_fail(
    auth_client, company_owner, company, company_branch
):
    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(company_branch.id),
        {"managers": [999_999]},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_assign_managers_other_company_branch_fail(
    auth_client,
    company_owner,
    company,
    other_company_branch,
    branch_manager_user_factory,
):
    manager = branch_manager_user_factory()

    response = auth_client(company_owner, company_id=company.id).post(
        assign_managers_url(other_company_branch.id),
        {"managers": [manager.id]},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_assign_managers_get_not_allowed_fail(
    auth_client, company_owner, company, company_branch
):
    response = auth_client(company_owner, company_id=company.id).get(
        assign_managers_url(company_branch.id)
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
