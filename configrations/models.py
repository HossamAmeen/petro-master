from django.db import models


class ConfigrationsModel(models.Model):
    term_conditions = models.TextField()
    privacy_policy = models.TextField()
    about_us = models.TextField()
    faq = models.TextField()
