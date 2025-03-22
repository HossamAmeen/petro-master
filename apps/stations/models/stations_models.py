from django.db import models

from apps.utilities.models.abstract_base_model import AbstractBaseModel


class Station(AbstractBaseModel):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    lang = models.FloatField()
    lat = models.FloatField()
    district = models.ForeignKey('geo.District', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Station'
        verbose_name_plural = 'Stations'


class StationBranch(AbstractBaseModel):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Station Branch'
        verbose_name_plural = 'Station Branches'


class StationService(AbstractBaseModel):
    name = models.CharField(max_length=255)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='station_services')

    class Meta:
        verbose_name = 'Station Service'
        verbose_name_plural = 'Station Services'
