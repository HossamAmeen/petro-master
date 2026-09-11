"""The dashboard onboards a company; its owner and branch managers log in."""

from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.auth.tests.helpers import company_login_url, decode_access, profile_url
from apps.companies.models.company_models import Company, CompanyBranch
from apps.users.models import CompanyUser, User

from .helpers import (
    assign_company_managers_url,
    company_branch_detail_url,
    login_client,
    sign_in,
)

pytestmark = [pytest.mark.django_db, pytest.mark.feature]

PASSWORD = "password123"


def branch_ids(response):
    return {item["id"] for item in response.data["results"]}


class TestCompanyOnboarding:
    @pytest.fixture(autouse=True)
    def setup(self, admin_user, geo_data):
        self.admin = sign_in("dashboard", admin_user)
        self.district = geo_data["district"]

    def create_company(self, name="Nile Transport"):
        response = self.admin.post(
            reverse("companies-list"),
            {
                "name": name,
                "email": "nile@example.com",
                "phone_number": "01511111111",
                "address": "Maadi",
                "district": self.district.id,
                "is_active": True,
            },
            format="json",
        )
        return response, Company.objects.filter(name=name).first()

    def create_branch(self, client, company, name):
        return client.post(
            reverse("company-branches-list"),
            {"name": name, "district": self.district.id, "company": company.id},
            format="json",
        )

    def test_dashboard_onboards_company_and_owner_logs_in_success(self, api_client):
        created, company = self.create_company()
        owner_created = self.admin.post(
            reverse("company-owners-list"),
            {
                "name": "Nile Owner",
                "phone_number": "01522222222",
                "password": PASSWORD,
                "company_id": company.id,
            },
            format="json",
        )
        first = self.create_branch(self.admin, company, "Cairo")
        second = self.create_branch(self.admin, company, "Giza")

        login = api_client.post(
            company_login_url(),
            {"identifier": "01522222222", "password": PASSWORD},
            format="json",
        )

        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert owner_created.status_code == status.HTTP_201_CREATED, owner_created.data
        assert first.status_code == status.HTTP_201_CREATED, first.data
        assert second.status_code == status.HTTP_201_CREATED, second.data
        owner = CompanyUser.objects.get(id=owner_created.data["id"])
        assert owner.role == User.UserRoles.CompanyOwner
        assert owner.email == "01522222222@petro.com"
        assert login.status_code == status.HTTP_200_OK, login.data
        branches = set(company.branches.values_list("id", flat=True))
        assert login.json()["company_id"] == company.id
        assert set(login.json()["branches"]) == branches
        assert decode_access(login.data["access"])["company_id"] == company.id

        owner_client = login_client("company", owner)
        listed = owner_client.get(reverse("company-branches-list"))
        profile = owner_client.get(profile_url())

        assert branch_ids(listed) == branches
        assert profile.data["balance"] == Decimal("0.00")

    def test_owner_cannot_create_branches_or_owners_fail(self, company, company_owner):
        owner = sign_in("company", company_owner)

        branch = self.create_branch(owner, company, "Owner Branch")
        another_owner = owner.post(
            reverse("company-owners-list"),
            {
                "name": "Second Owner",
                "phone_number": "01533333333",
                "password": PASSWORD,
                "company_id": company.id,
            },
            format="json",
        )

        assert branch.status_code == status.HTTP_403_FORBIDDEN
        assert another_owner.status_code == status.HTTP_403_FORBIDDEN
        assert not CompanyBranch.objects.filter(name="Owner Branch").exists()

    def test_branch_manager_created_through_api_is_an_owner_fail(
        self, company, company_owner, company_branch, second_company_branch
    ):
        """Open issue: `company-branch-managers` POST uses the owner serializer,
        so the new user is a company owner. `assign-managers` then rejects them,
        and no endpoint can create a real branch manager."""
        owner = sign_in("company", company_owner)

        created = owner.post(
            reverse("company-branch-managers-list"),
            {
                "name": "Would-be Manager",
                "phone_number": "01544444444",
                "password": PASSWORD,
                "company_id": company.id,
            },
            format="json",
        )
        manager = CompanyUser.objects.get(phone_number="01544444444")
        assigned = owner.post(
            assign_company_managers_url(company_branch.id),
            {"managers": [manager.id]},
            format="json",
        )
        as_manager = login_client("company", manager)

        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert manager.role == User.UserRoles.CompanyOwner
        assert assigned.status_code == status.HTTP_400_BAD_REQUEST
        assert not company_branch.managers.exists()
        # as an owner they see every branch of the company
        assert branch_ids(as_manager.get(reverse("company-branches-list"))) == {
            company_branch.id,
            second_company_branch.id,
        }

    def test_assigned_branch_manager_sees_only_their_branch_success(
        self,
        company_owner,
        company_branch,
        second_company_branch,
        branch_manager_user_factory,
    ):
        # no endpoint creates a real branch manager (see the test above)
        manager = branch_manager_user_factory()
        company_branch.balance = Decimal("250.00")
        company_branch.save(update_fields=["balance"])
        owner = sign_in("company", company_owner)

        assigned = owner.post(
            assign_company_managers_url(company_branch.id),
            {"managers": [manager.id]},
            format="json",
        )
        as_manager = sign_in("company", manager)
        listed = as_manager.get(reverse("company-branches-list"))
        other_branch = as_manager.get(
            company_branch_detail_url(second_company_branch.id)
        )
        profile = as_manager.get(profile_url())

        assert assigned.status_code == status.HTTP_200_OK, assigned.data
        assert branch_ids(listed) == {company_branch.id}
        assert other_branch.status_code == status.HTTP_404_NOT_FOUND
        assert profile.data["balance"] == Decimal("250.00")
