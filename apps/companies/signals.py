from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.companies.helper import send_cash_request_otp
from apps.companies.models.company_cash_models import CompanyCashRequest


@receiver(post_save, sender=CompanyCashRequest)
def send_fcm_message_after_notification_created(sender, instance, created, **kwargs):
    if created:
        send_cash_request_otp(instance)
