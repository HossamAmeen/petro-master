from faker import Faker

from apps.companies.models.company_models import Company, CompanyBranch, Driver
from apps.geo.models import District

fake = Faker()
district = District.objects.first()
dashboard_company = Company.objects.first()
dashboard_company_branch = CompanyBranch.objects.first()
for _ in range(100):
    Driver.objects.create(
        name=fake.name(),
        phone_number=fake.phone_number()[:11],
        lincense_number=fake.license_plate(),
        lincense_expiration_date=fake.date(),
        branch=dashboard_company_branch,
        created_by_id=15,
        updated_by_id=15,
    )
