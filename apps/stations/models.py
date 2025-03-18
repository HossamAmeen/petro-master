from django.db import models


class Station(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    lang = models.FloatField()
    lat = models.FloatField()

    class Meta:
        verbose_name = 'Station'
        verbose_name_plural = 'Stations'


class StationBranch(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Station Branch'
        verbose_name_plural = 'Station Branches'


class StationService(models.Model):
    name = models.CharField(max_length=255)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Station Service'
        verbose_name_plural = 'Station Services'
