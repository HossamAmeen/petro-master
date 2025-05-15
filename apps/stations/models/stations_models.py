from django.db import models

from apps.stations.models.service_models import Service
from apps.utilities.models.abstract_base_model import AbstractBaseModel


class Station(AbstractBaseModel):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    lang = models.FloatField()
    lat = models.FloatField()
    district = models.ForeignKey(
        "geo.District", on_delete=models.SET_NULL, null=True, blank=True
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Station"
        verbose_name_plural = "Stations"


class StationBranch(AbstractBaseModel):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    lang = models.FloatField()
    lat = models.FloatField()
    district = models.ForeignKey(
        "geo.District", on_delete=models.SET_NULL, null=True, blank=True
    )
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="branches"
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Station Branch"
        verbose_name_plural = "Station Branches"

    def __str__(self):
        return self.name


class StationService(AbstractBaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="station_services"
    )

    def __str__(self):
        return f"{self.service.name} - {self.station.name}"

    class Meta:
        verbose_name = "Station Service"
        verbose_name_plural = "Station Services"


class StationBranchService(AbstractBaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    station_branch = models.ForeignKey(
        StationBranch, on_delete=models.CASCADE, related_name="station_branch_services"
    )

    def __str__(self):
        return f"{self.service.name} - {self.station_branch.name}"

    class Meta:
        verbose_name = "Station Branch Service"
        verbose_name_plural = "Station Branch Services"
