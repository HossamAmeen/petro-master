from unittest.mock import MagicMock, patch

import pytest

from apps.auth.utils import send_email_via_sendgrid

pytestmark = [pytest.mark.api]


class TestUtils:

    @patch("apps.auth.utils.SendGridAPIClient")
    def test_send_email_via_sendgrid_success(self, mock_client_cls, settings):
        settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
        settings.SENDGRID_API_KEY = "sg-test-key"
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b"accepted"
        mock_response.headers = {"X-Message-Id": "abc"}
        mock_client_cls.return_value.send.return_value = mock_response

        status_code, body, headers = send_email_via_sendgrid(
            "user@example.com",
            "Reset Password",
            "<p>Hello</p>",
        )

        assert status_code == 202
        assert body == b"accepted"
        assert headers == {"X-Message-Id": "abc"}
        mock_client_cls.assert_called_once_with("sg-test-key")
        mock_client_cls.return_value.send.assert_called_once()

    @patch("apps.auth.utils.SendGridAPIClient")
    def test_send_email_via_sendgrid_client_error_fail(self, mock_client_cls, settings):
        settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
        settings.SENDGRID_API_KEY = "sg-test-key"
        mock_client_cls.side_effect = Exception("sendgrid down")

        status_code, body, headers = send_email_via_sendgrid(
            "user@example.com",
            "Reset Password",
            "<p>Hello</p>",
        )

        assert status_code is None
        assert body == "sendgrid down"
        assert headers is None

    @patch("apps.auth.utils.SendGridAPIClient")
    def test_send_email_via_sendgrid_send_error_fail(self, mock_client_cls, settings):
        settings.DEFAULT_FROM_EMAIL = "noreply@example.com"
        settings.SENDGRID_API_KEY = "sg-test-key"
        mock_client_cls.return_value.send.side_effect = Exception("rejected")

        status_code, body, headers = send_email_via_sendgrid(
            "user@example.com",
            "Reset Password",
            "<p>Hello</p>",
        )

        assert status_code is None
        assert body == "rejected"
        assert headers is None
