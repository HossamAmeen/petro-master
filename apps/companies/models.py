from django.db import models
from django_extensions.db.models import TimeStampedModel
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class Company(TimeStampedModel):
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


class CompanyBranch(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    district = models.ForeignKey('geo.District', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Company Branch'
        verbose_name_plural = 'Company Branches'


class Car(AbstractBaseModel):
    code = models.CharField(max_length=10, unique=True, verbose_name="car code")
    plate = models.CharField(max_length=10, verbose_name="car number plate")
    color = models.CharField(max_length=10)
    license_expiration_date = models.DateField()
    model_year = models.IntegerField()
    brand = models.CharField(max_length=25)
    is_with_odometer = models.BooleanField()
    tank_capacity = models.IntegerField()
    permitted_fuel_amount = models.IntegerField()
    fuel_type = models.CharField(max_length=10)
    number_of_fuelings_per_day = models.IntegerField()
    fuel_allowed_days = models.JSONField(default=list, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    city = models.ForeignKey('geo.City', on_delete=models.SET_NULL, null=True, blank=True)
    branch = models.ForeignKey(CompanyBranch, on_delete=models.CASCADE)

    def __str__(self):
        return self.code + " - " + self.plate
    
    class Meta:
        verbose_name = 'Car'
        verbose_name_plural = 'Cars'
