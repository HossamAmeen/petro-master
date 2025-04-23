from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.fcm_manager import FCMManager
from apps.notifications.models import Notification


@receiver(post_save, sender=Notification)
def send_fcm_message_after_notification_created(sender, instance, created, **kwargs):
    if created:
        FCMManager.send_fcm_message(
            title=instance.title,
            body=instance.description,
            device_tokens=list(
                instance.user.firebase_tokens.values_list("token", flat=True)
            ),
        )
