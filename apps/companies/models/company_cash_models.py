from django.core.validators import MinValueValidator
from django.db import models

from apps.companies.models.company_models import Company, Driver
from apps.shared.generate_code import generate_unique_code
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import User
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class CompanyCashRequest(AbstractBaseModel):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress"
        APPROVED = "approved"
        REJECTED = "rejected"

    code = models.CharField(max_length=10, blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
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
    station_branch = models.ForeignKey(
        StationBranch, on_delete=models.SET_NULL, null=True, blank=True
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_code(model=self.__class__)
        if not self.otp:
            self.otp = generate_unique_code(model=self.__class__)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Company Cash Request"
        verbose_name_plural = "6. Company Cash Requests"
