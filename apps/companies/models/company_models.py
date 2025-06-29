import base64
import os
from io import BytesIO

import qrcode
from django.core.exceptions import ValidationError
from django.db import models
from django.db.utils import settings
from django.utils import timezone

from apps.shared.generate_code import generate_unique_code
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class Company(AbstractBaseModel):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)
    district = models.ForeignKey(
        "geo.District", on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "1. Companies"


class CompanyBranch(AbstractBaseModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="branches"
    )
    district = models.ForeignKey(
        "geo.District", on_delete=models.SET_NULL, null=True, blank=True
    )
    fees = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    other_service_fees = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.0
    )
    cash_request_fees = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    def __str__(self):
        return self.name + " - " + self.company.name

    class Meta:
        verbose_name = "Company Branch"
        verbose_name_plural = "2. Company Branches"


class Car(AbstractBaseModel):
    class FuelType(models.TextChoices):
        DIESEL = "Diesel"
        SOLAR = "Solar"
        GASOLINE = "Gasoline"
        NATURAL_GAS = "Natural_Gas"
        ELECTRIC = "Electric"
        HYDROGEN = "Hydrogen"

    class FuelAllowedDay(models.TextChoices):
        MON = "Monday"
        TUE = "Tuesday"
        WED = "Wednesday"
        THU = "Thursday"
        FRI = "Friday"
        SAT = "Saturday"
        SUN = "Sunday"

    class PlateColor(models.TextChoices):
        RED = "Red"
        BLUE = "Blue"
        ORANGE = "Orange"
        YELLOW = "Yellow"
        GREEN = "Green"
        GOLD = "Gold"

    code = models.CharField(max_length=10, unique=True, verbose_name="car code")
    plate_number = models.CharField(
        max_length=10, null=True, blank=True, verbose_name="car number plate"
    )
    plate_character = models.CharField(
        max_length=10, null=True, blank=True, verbose_name="car plate character"
    )
    plate_color = models.CharField(max_length=10, choices=PlateColor.choices)
    color = models.CharField(max_length=10)

    license_expiration_date = models.DateField(null=True, blank=True)
    examination_date = models.DateField(null=True, blank=True)

    model_year = models.IntegerField()
    brand = models.CharField(max_length=25)

    is_with_odometer = models.BooleanField()
    tank_capacity = models.IntegerField()
    permitted_fuel_amount = models.IntegerField()
    fuel_type = models.CharField(
        max_length=20,
        choices=FuelType.choices,
        null=True,
        blank=True,
        default=FuelType.DIESEL,
    )
    service = models.ForeignKey(
        "stations.Service", on_delete=models.SET_NULL, null=True, blank=True
    )
    oil_type = models.CharField(max_length=20, null=True, blank=True)
    last_meter = models.IntegerField(null=True, blank=True, default=0)
    fuel_consumption_rate = models.IntegerField(default=0)
    number_of_fuelings_per_day = models.IntegerField()
    number_of_washes_per_month = models.IntegerField()
    fuel_allowed_days = models.JSONField(default=list, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_blocked_balance_update = models.BooleanField(default=False)
    city = models.ForeignKey(
        "geo.City", on_delete=models.SET_NULL, null=True, blank=True
    )
    branch = models.ForeignKey(
        CompanyBranch, on_delete=models.CASCADE, related_name="cars"
    )

    def __str__(self):
        return (
            self.plate_character + " - " + self.plate_number
            if self.plate_number
            else self.code
        )

    def clean(self):
        if self.permitted_fuel_amount > self.tank_capacity:
            raise ValidationError("الكمية المسموح بها أكبر من حجم المخزون")

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_code(Car)
        super().save(*args, **kwargs)

    @property
    def plate(self):
        return (
            self.plate_character + " " + self.plate_number if self.plate_number else ""
        )

    def is_available_today(self):
        today = timezone.now().date()
        return today.strftime("%A") in self.fuel_allowed_days

    class Meta:
        verbose_name = "Car"
        verbose_name_plural = "3. Cars"


class CarCode(AbstractBaseModel):
    code = models.CharField(max_length=10, unique=True, verbose_name="car code")
    car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def qr_code_base64(self):
        qr = qrcode.QRCode(
            version=1,
            box_size=12,  # Increased from 10 to make QR bigger
            border=4,  # Increased border
        )
        qr.add_data(self.code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()

    @property
    def logo_base64(self):
        logo_path = os.path.join(settings.STATIC_ROOT, "admin/img/logo.png")
        try:
            with open(logo_path, "rb") as logo_file:
                return base64.b64encode(logo_file.read()).decode()
        except Exception:
            return None


class Driver(AbstractBaseModel):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=11)
    code = models.CharField(max_length=10, unique=True, verbose_name="driver code")
    lincense_number = models.CharField(
        max_length=20, unique=True, verbose_name="driver license number"
    )
    lincense_expiration_date = models.DateField()
    branch = models.ForeignKey(
        CompanyBranch, on_delete=models.CASCADE, related_name="drivers"
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_code(Driver)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Driver"
        verbose_name_plural = "4. Drivers"
