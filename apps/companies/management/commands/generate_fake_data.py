from django.core.management import call_command
from django.core.management.base import BaseCommand
from faker import Faker

from apps.companies.factories import (
    CarFactory,
    CityFactory,
    CompanyBranchFactory,
    CompanyFactory,
    DistrictFactory,
    DriverFactory,
    NotificationFactory,
    StationFactory,
    StationServiceFactory,
    UserFactory,
)
from apps.companies.models.company_models import Company, CompanyBranch
from apps.geo.models import City, District
from apps.users.models import CompanyBranchManager, CompanyUser, User

fake = Faker()


class Command(BaseCommand):
    help = "Generate fake data for companies, branches, cars, and drivers"

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS("Generating fake data using Factory Boy..."))
        call_command("loaddata", "fixtures/users.json")
        call_command("loaddata", "fixtures/countries.json")
        city = City.objects.create(name="Cairo", country_id=1)
        district = District.objects.create(name="New Cairo", city=city)
        company = Company.objects.create(
            name="Petro company",
            address="343 Zachary Alley\nEdwardbury, RI 32596",
            balance="31498.53",
            email="petro_company@silva.net",
            phone_number="01578945562",
            district=district,
            created_by_id=1,
            updated_by_id=1
        )
        if not CompanyUser.objects.filter(phone_number="01010079791", email="petro_company@petro.com").exists():
            company_user = CompanyUser.objects.create(
                name="petro company",
                email="petro_company@petro.com",
                phone_number="01010079791",
                role=User.UserRoles.CompanyOwner,
                company=company,
                created_by_id=1,
                updated_by_id=1
            )
            company_user.set_password("admin")
            company_user.save()
        company_branch_manager = CompanyUser.objects.filter(phone_number="01010079792", email="petro_company_manager@petro.com").first()
        if not company_branch_manager:
            company_branch_manager = CompanyUser.objects.create(
                name="petro company manager",
                email="petro_company_manager@petro.com",
                phone_number="01010079792",
                role=User.UserRoles.CompanyBranchManager,
                company=company,
                created_by_id=1,
                updated_by_id=1
            )
            company_branch_manager.set_password("admin")
            company_branch_manager.save()

        # Generate data
        UserFactory.create_batch(10)
        CityFactory.create_batch(5)
        DistrictFactory.create_batch(5)
        CompanyFactory.create_batch(5)
        CompanyBranchFactory.create_batch(25)
        CarFactory.create_batch(20)
        DriverFactory.create_batch(90)
        NotificationFactory.create_batch(50)
        StationFactory.create_batch(25)
        StationServiceFactory.create_batch(50)
        CompanyBranchManager.objects.create(
            user=company_branch_manager,
            company_branch=CompanyBranch.objects.first(),
            created_by_id=1,
            updated_by_id=1
        )

        self.stdout.write(self.style.SUCCESS(
            "Created 5 companies, 5 branches, 20 cars, 5 cities, 5 districts, 50 notifications, 25 stations and 90 drivers successfully."))
