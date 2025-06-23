from django.core.management.base import BaseCommand

from apps.companies.models.company_models import Company, CompanyBranch
from apps.geo.models import District
from apps.users.models import CompanyBranchManager, CompanyUser, User


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        district = District.objects.get(name="New Cairo")
        admin_user = User.objects.get(phone_number="01010079798")
        company = Company.objects.filter(id=1).first()
        if not company:
            company = Company.objects.create(
                name="google company",
                address="new Cairo",
                balance=10000.00,
                email="test_company@gmail.com",
                phone_number="01712345678",
                district=district,
                fees=10.00,
                created_by=admin_user,
                updated_by=admin_user,
                created="2025-06-23T20:56:17.000Z",
                modified="2025-06-23T20:56:17.000Z",
            )
        google_company_owner = CompanyUser.objects.create(
            name="google company owner",
            email="test_company_owner@gmail.com",
            phone_number="01712345678",
            role=User.UserRoles.CompanyOwner,
            company=company,
            created_by=admin_user,
            updated_by=admin_user,
        )
        google_company_owner.set_password("admin")
        google_company_owner.save()

        google_company_branch = CompanyBranch.objects.create(
            name="google branch",
            email="test_branch@gmail.com",
            phone_number="01712345678",
            balance=10000.00,
            company=company,
            district=district,
            created_by=admin_user,
            updated_by=admin_user,
        )

        test_google_manager = CompanyUser.objects.create(
            name="google company branch manager",
            email="test_company_manager@gmail.com",
            phone_number="01712345679",
            role=User.UserRoles.CompanyBranchManager,
            company=company,
            created_by=admin_user,
            updated_by=admin_user,
        )

        test_google_manager.set_password("admin")
        test_google_manager.save()

        CompanyBranchManager.objects.create(
            company_branch=google_company_branch,
            user=test_google_manager,
            created_by=admin_user,
            updated_by=admin_user,
        )
