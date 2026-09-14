from unittest.mock import patch

from apps.shared.send_sms import send_sms


class TestSendSms:

    @patch("apps.shared.send_sms.requests.request")
    def test_outside_production_does_not_call_gateway_success(self, request, settings):
        settings.ENVIRONMENT = "staging"

        assert send_sms("hello", "01000000000") is None

        request.assert_not_called()

    @patch("apps.shared.send_sms.requests.request")
    def test_production_calls_gateway_and_logs_response_success(
        self, request, settings, caplog
    ):
        settings.ENVIRONMENT = "PRODUCTION"
        settings.SMS_SMART_EGYPT_USERNAME = "user"
        settings.SMS_SMART_EGYPT_PASSWORD = "secret"
        settings.SMS_SMART_EGYPT_SENDER_NAME = "Petro"
        request.return_value.text = "OK: queued"

        with caplog.at_level("INFO", logger="apps.shared.send_sms"):
            send_sms("hello", "01000000000")

        request.assert_called_once_with(
            "GET",
            "https://smssmartegypt.com/sms/api/?username=user&password=secret"
            "&sendername=Petro&message=hello&mobiles=01000000000",
        )
        assert "OK: queued" in caplog.text
