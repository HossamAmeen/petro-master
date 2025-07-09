from django.core.management.base import BaseCommand
from faker import Faker

from apps.companies.management.commands.codes import codes
from apps.companies.models.company_models import Car, CarCode

fake = Faker()


class Command(BaseCommand):
    help = "Add real codes to database."

    def handle(self, *args, **options):
        if CarCode.objects.filter(code__in=codes).exists():
            self.stdout.write(
                self.style.SUCCESS(
                    "Real codes already exist in database."
                    + str(
                        CarCode.objects.filter(code__in=codes).values_list(
                            "code", flat=True
                        )
                    )
                )
            )
            return
        if Car.objects.filter(code__in=codes).exists():
            self.stdout.write(
                self.style.SUCCESS(
                    "Real codes already exist in database."
                    + str(
                        Car.objects.filter(code__in=codes).values_list(
                            "code", flat=True
                        )
                    )
                )
            )
            return
        CarCode.objects.bulk_create([CarCode(code=code) for code in codes])
        self.stdout.write(
            self.style.SUCCESS("Added real codes to database successfully.")
        )
