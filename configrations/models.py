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
    whatsapp_number = models.CharField(max_length=150, null=True, blank=True)
    telegram_link = models.URLField(null=True, blank=True)
    facebook_link = models.URLField(null=True, blank=True)
    instagram_link = models.URLField(null=True, blank=True)
    twitter_link = models.URLField(null=True, blank=True)
    x_link = models.URLField(null=True, blank=True)
    youtube_link = models.URLField(null=True, blank=True)
    linkedin_link = models.URLField(null=True, blank=True)
    android_app_link = models.URLField(null=True, blank=True)
    ios_app_link = models.URLField(null=True, blank=True)


class Slider(models.Model):
    name = models.CharField(max_length=255, default="")
    image = models.FileField()
    order = models.IntegerField(default=0)
