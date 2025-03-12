from django.db import models
from django_extensions.db.models import TimeStampedModel


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
