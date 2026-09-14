from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.notifications.tasks import send_fcm_message_task
from apps.shared.task_runner import run_task


@receiver(post_save, sender=Notification)
def send_fcm_message_after_notification_created(sender, instance, created, **kwargs):
    if created:
        run_task(
            send_fcm_message_task,
            title=instance.title,
            body=instance.description,
            device_tokens=list(
                instance.user.firebase_tokens.values_list("token", flat=True)
            ),
        )
