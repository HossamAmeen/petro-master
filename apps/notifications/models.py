from django.db import models
from django_extensions.db.models import TimeStampedModel


class Notification(TimeStampedModel):

    class NotificationType(models.TextChoices):
        FUEL = "fuel"
        MONEY = "money"
        GENERAL = "general"
        STATION_WORKER = "station_worker"
        STATION_SERVICE = "station_service"

    description = models.TextField()
    is_read = models.BooleanField(default=False)
    title = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=NotificationType.choices)
    is_success = models.BooleanField(default=False)
    user = models.ForeignKey(
        "users.User", on_delete=models.SET_NULL,
    null=True,
        blank=True,
        help_text="The user that this notification is for. If the user is deleted, the notification will be set to null."
    )
    url = models.URLField(null=True, blank=True)
