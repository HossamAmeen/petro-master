from django.db import models
from django_extensions.db.models import TimeStampedModel


class AbstractBaseModel(TimeStampedModel):
    created_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="created_%(class)ss")
    updated_by = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name="updated_%(class)ss")

    class Meta:
        abstract = True
