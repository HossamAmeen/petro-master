from django.db import models
from django_extensions.db.models import TimeStampedModel


class Company(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=11)

    def __str__(self):
        return self.name


class CompanyBranch(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone_number = models.CharField(max_length=11)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    def __str__(self):
        return self.name