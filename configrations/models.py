from django.db import models


class ConfigrationsModel(models.Model):
    term_conditions = models.TextField()
    privacy_policy = models.TextField()
    about_us = models.TextField()
    faq = models.TextField()
    app_version = models.CharField(max_length=255, default="1.0.0")
    company_support_email = models.EmailField(null=True, blank=True)
    company_support_phone = models.CharField(max_length=255, null=True, blank=True)
    company_support_address = models.TextField(null=True, blank=True)
    company_support_name = models.CharField(max_length=255, null=True, blank=True)
    station_support_email = models.EmailField(null=True, blank=True)
    station_support_phone = models.CharField(max_length=255, null=True, blank=True)
    station_support_address = models.TextField(null=True, blank=True)
    station_support_name = models.CharField(max_length=255, null=True, blank=True)


class Slider(models.Model):
    image = models.FileField()
    order = models.IntegerField(default=0)
