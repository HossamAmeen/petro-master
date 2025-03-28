import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.utilities.models.abstract_base_model import AbstractBaseModel


class Company(AbstractBaseModel):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)
    district = models.ForeignKey('geo.District', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'


class CompanyBranch(AbstractBaseModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    district = models.ForeignKey('geo.District', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Company Branch'
        verbose_name_plural = 'Company Branches'


class Car(AbstractBaseModel):
    class FuelType(models.TextChoices):
        DIESEL = 'Diesel'
        GASOLINE = 'Gasoline'
        ELECTRIC = 'Electric'
        HYDROGEN = 'Hydrogen'

    class FuelAllowedDay(models.TextChoices):
        MON = 'Monday'
        TUE = 'Tuesday'
        WED = 'Wednesday'
        THU = 'Thursday'
        FRI = 'Friday'
        SAT = 'Saturday'
        SUN = 'Sunday'

    code = models.CharField(max_length=10, unique=True, verbose_name="car code")
    plate = models.CharField(max_length=10, verbose_name="car number plate")
    plate_color = models.CharField(max_length=10)
    color = models.CharField(max_length=10)
    license_expiration_date = models.DateField()
    model_year = models.IntegerField()
    brand = models.CharField(max_length=25)
    is_with_odometer = models.BooleanField()
    tank_capacity = models.IntegerField()
    permitted_fuel_amount = models.IntegerField()
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices)
    number_of_fuelings_per_day = models.IntegerField()
    number_of_washes_per_month = models.IntegerField()
    fuel_allowed_days = models.JSONField(default=list, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    city = models.ForeignKey('geo.City', on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(CompanyBranch, on_delete=models.CASCADE, related_name='cars')

    def __str__(self):
        return self.code + " - " + self.plate

    def clean(self):
        if self.permitted_fuel_amount > self.tank_capacity:
            raise ValidationError('Permitted fuel amount must be less than or equal to tank capacity.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Car'
        verbose_name_plural = 'Cars'


class Driver(AbstractBaseModel):
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=11)
    code = models.CharField(max_length=10, unique=True, verbose_name="driver code")
    lincense_number = models.CharField(max_length=20, unique=True, verbose_name="driver license number")
    lincense_expiration_date = models.DateField()
    branch = models.ForeignKey(CompanyBranch, on_delete=models.CASCADE, related_name='drivers')

    def __str__(self):
        return self.name

    def generate_unique_code(self):
        """Generate a unique alphanumeric code."""
        while True:
            new_code = f"DR-{uuid.uuid4().hex[:10].upper()}"  # Example: DR-ABC123
            if not Driver.objects.filter(code=new_code).exists():
                return new_code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Driver'
        verbose_name_plural = 'Drivers'
