import requests
from celery import shared_task

from apps.notifications.fcm_manager import FCMManager
from apps.shared.send_sms import send_sms


# No Celery retries: the Firebase SDK already retries 500/503 responses and
# dropped connections, and send_each reports per-token failures instead of
# raising, so there is nothing left to retry on here.
@shared_task(ignore_result=True)
def send_fcm_message_task(title: str, body: str, device_tokens: list[str]) -> None:
    """Push a notification to every device in ``device_tokens``."""
    FCMManager.send_fcm_message(title=title, body=body, device_tokens=device_tokens)


# Only transient network failures are worth another attempt.
@shared_task(
    autoretry_for=(requests.ConnectionError, requests.Timeout),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
    ignore_result=True,
)
def send_sms_task(message: str, receiver: str) -> None:
    """Text ``message`` to the ``receiver`` phone number."""
    send_sms(message, receiver)
