from smtplib import SMTPServerDisconnected
from unittest.mock import patch

from django.core import mail

from apps.auth.tasks import send_password_reset_email_task

EMAIL = "user@example.com"
RESET_LINK = "https://api.example.com/api/v1/auth/password-reset-confirm/abc/"


class TestSendPasswordResetEmailTask:

    def test_sends_reset_link_success(self):
        send_password_reset_email_task(EMAIL, RESET_LINK)

        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.subject == "Password Reset Request"
        assert sent.to == [EMAIL]
        assert RESET_LINK in sent.alternatives[0][0]

    def test_smtp_error_is_retried_on_worker_fail(self):
        with patch(
            "apps.auth.tasks.send_mail", side_effect=SMTPServerDisconnected("gone")
        ) as send_mail:
            # apply() runs the task the way a worker does, retries included.
            result = send_password_reset_email_task.apply(args=(EMAIL, RESET_LINK))

        assert result.failed()
        assert isinstance(result.result, SMTPServerDisconnected)
        assert send_mail.call_count == 4  # first attempt + 3 retries
