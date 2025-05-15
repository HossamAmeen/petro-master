from django.db import models

from apps.companies.models.company_models import Car, Driver
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import StationBranch
from apps.users.models import Worker
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class CarOperation(AbstractBaseModel):
    class OperationStatus(models.TextChoices):
        PENDING = "pending"
        COMPLETED = "completed"
        CANCELLED = "cancelled"

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=OperationStatus.choices, default=OperationStatus.PENDING
    )
    code = models.CharField(max_length=50)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fuel_type = models.CharField(
        max_length=20,
        choices=Car.FuelType.choices,
        default=Car.FuelType.DIESEL,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(
        max_length=20,
        choices=Service.ServiceUnit.choices,
        default=Service.ServiceUnit.OTHER,
    )
    car_meter = models.IntegerField()
    fuel_consumption_rate = models.IntegerField(null=True, blank=True)
    motor_image = models.ImageField(upload_to="motor_images/", null=True, blank=True)
    fuel_image = models.ImageField(upload_to="fuel_images/", null=True, blank=True)

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
        Service, on_delete=models.CASCADE, related_name="operations"
    )

    class Meta:
        verbose_name = "Car Operation"
        verbose_name_plural = "5. Car Operations"

    def __str__(self):
        return f"{self.car} - {self.service} - {self.code}"
