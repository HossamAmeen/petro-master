from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


# SMTP errors and socket errors (refused, timed out, DNS) are all OSErrors.
@shared_task(
    autoretry_for=(OSError,),
    retry_backoff=5,
    retry_kwargs={"max_retries": 3},
    ignore_result=True,
)
def send_password_reset_email_task(email: str, reset_link: str) -> None:
    """Email the password-reset link to ``email``."""
    send_mail(
        subject="Password Reset Request",
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
        html_message=render_to_string(
            "reset_password_email_template.html", {"reset_password_url": reset_link}
        ),
    )
