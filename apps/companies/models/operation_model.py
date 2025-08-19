from django.db import models

from apps.companies.models.company_models import Car, Driver
from apps.shared.generate_code import generate_unique_code
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import StationBranch
from apps.users.models import Worker
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class CarOperation(AbstractBaseModel):
    class OperationStatus(models.TextChoices):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=OperationStatus.choices, default=OperationStatus.PENDING
    )
    code = models.CharField(max_length=50)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    company_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    station_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    profits = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    fuel_type = models.CharField(
        max_length=20,
        choices=Car.FuelType.choices,
        null=True,
        blank=True,
    )  # may be removed
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    unit = models.CharField(
        max_length=20,
        choices=Service.ServiceUnit.choices,
        null=True,
        blank=True,
    )
    car_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    car_last_meter = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    fuel_consumption_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    motor_image = models.ImageField(upload_to="motor_images/", null=True, blank=True)
    fuel_image = models.ImageField(upload_to="fuel_images/", null=True, blank=True)
    car_image = models.ImageField(upload_to="car_images/", null=True, blank=True)

    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="operations")
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name="operations"
    )
    station_branch = models.ForeignKey(
        StationBranch, on_delete=models.CASCADE, related_name="operations"
    )
    worker = models.ForeignKey(
        Worker, on_delete=models.CASCADE, related_name="operations"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operations",
    )

    class Meta:
        verbose_name = "Car Operation"
        verbose_name_plural = "5. Car Operations"

    def __str__(self):
        return f"{self.car} - {self.service} - {self.code}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = generate_unique_code(self.__class__)
        super().save(*args, **kwargs)
