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

fake = Faker()


class Command(BaseCommand):
    help = "Generate fake data for companies, branches, cars, and drivers"

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS("Generating fake data using Factory Boy..."))
        call_command("loaddata", "fixtures/users.json")
        call_command("loaddata", "fixtures/countries.json")

        # Generate data
        UserFactory.create_batch(10)
        CityFactory.create_batch(5)
        DistrictFactory.create_batch(5)
        CompanyFactory.create_batch(5)
        CompanyBranchFactory.create_batch(5)
        CarFactory.create_batch(20)
        DriverFactory.create_batch(15)
        NotificationFactory.create_batch(50)
        StationFactory.create_batch(25)
        StationServiceFactory.create_batch(50)

        self.stdout.write(self.style.SUCCESS(
            "Created 5 companies, 5 branches, 20 cars, 5 cities, 5 districts, 50 notifications, 25 stations and 15 drivers successfully."))
