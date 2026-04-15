import pytest

from apps.companies.models.company_models import Company, CompanyBranch
from apps.users.models import CompanyBranchManager, CompanyUser, User


@pytest.fixture
def company(db, geo_data):
    return Company.objects.create(
        name="Company 1",
        address="Company Address 1",
        district=geo_data["district"],
    )

@pytest.fixture
def company_owner(db, admin_user, company):
    return CompanyUser.objects.create(
        name="Company Owner 1",
        phone_number="01000000005",
        email="company_owner@example.com",
        password="password123",
        role=User.UserRoles.CompanyOwner,
        company=company,
        created_by=admin_user,
    )

@pytest.fixture
def company_branch(db, company, geo_data):
    return CompanyBranch.objects.create(
        name="Company Branch 1",
        company=company,
        district=geo_data["district"],
    )

@pytest.fixture
def company_branch_manager(db, admin_user, company_branch, company):
    manager_user = CompanyUser.objects.create(
        name="Company Branch Manager 1",
        phone_number="01000000006",
        email="company_branch_manager@example.com",
        password="password123",
        role=User.UserRoles.CompanyBranchManager,
        company=company,
        created_by=admin_user,
    )
    CompanyBranchManager.objects.create(
        company_branch=company_branch,
        user=manager_user,
        created_by=admin_user,
    )
    return manager_user
