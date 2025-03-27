from django.db import models

from apps.utilities.models.abstract_base_model import AbstractBaseModel


class Station(AbstractBaseModel):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    lang = models.FloatField()
    lat = models.FloatField()
    district = models.ForeignKey('geo.District', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name

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

class Service(AbstractBaseModel):
    class ServiceType(models.TextChoices):
        PETROL = 'petrol'
        DIESEL = 'diesel'
        WASH = 'wash'
        OTHER = 'other'

    class ServiceUnit(models.TextChoices):
        LITRE = 'litre'
        UNIT = 'unit'
        OTHER = 'other'

    name = models.CharField(max_length=25)
    unit = models.CharField(max_length=20, choices=ServiceUnit.choices, default=ServiceUnit.OTHER)
    type = models.CharField(max_length=25, choices=ServiceType.choices, default=ServiceType.OTHER)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'


class StationService(AbstractBaseModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name='station_services')

    def __str__(self):
        return f'{self.service.name} - {self.station.name}'

    class Meta:
        verbose_name = 'Station Service'
        verbose_name_plural = 'Station Services'
