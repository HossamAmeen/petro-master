from django.core.validators import MinValueValidator
from django.db import models

from apps.companies.models.company_models import Company, Driver
from apps.stations.models.stations_models import Station
from apps.users.models import User
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class CompanyCashRequest(AbstractBaseModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        APPROVED = "approved"
        REJECTED = "rejected"

    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(1)]
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="cash_requests"
    )
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    station = models.ForeignKey(
        Station, on_delete=models.SET_NULL, null=True, blank=True
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Company Cash Request"
        verbose_name_plural = "6. Company Cash Requests"
