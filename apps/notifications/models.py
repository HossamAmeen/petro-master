from django.db import models
from django_extensions.db.models import TimeStampedModel


class Notification(TimeStampedModel):
    description = models.TextField()
    is_read = models.BooleanField(default=False)
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20)
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
