from django.core.management.base import BaseCommand
from faker import Faker
from apps.companies.factories import CompanyFactory, CompanyBranchFactory, CarFactory, DriverFactory, UserFactory, NotificationFactory
from django.core.management import call_command


fake = Faker()


class Command(BaseCommand):
    help = "Generate fake data for companies, branches, cars, and drivers"

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS("Generating fake data using Factory Boy..."))
        call_command("loaddata", "fixtures/users.json")
        # Generate data
        UserFactory.create_batch(10)
        CompanyFactory.create_batch(5)
        CompanyBranchFactory.create_batch(5)
        CarFactory.create_batch(20)
        DriverFactory.create_batch(15)
        NotificationFactory.create_batch(10)

        self.stdout.write(self.style.SUCCESS(
            f"Created 5 companies, 5 branches, 20 cars, and 15 drivers."))