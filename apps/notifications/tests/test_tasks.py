from unittest.mock import patch

import pytest
import requests

from apps.notifications.tasks import send_fcm_message_task, send_sms_task

MESSAGE = "Your code is 123456"
PHONE = "01000000000"


class TestSendFcmMessageTask:

    def test_forwards_to_fcm_manager_success(self, mock_firebase_notifications):
        send_fcm_message_task("Fuel done", "Operation completed", ["token-1"])

        mock_firebase_notifications.assert_called_once_with(
            title="Fuel done", body="Operation completed", device_tokens=["token-1"]
        )


class TestSendSmsTask:
    """``apply()`` runs the task the way a worker does, retries included."""

    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("apps.notifications.tasks.send_sms") as send_sms:
            self.send_sms = send_sms
            yield

    def test_sends_sms_success(self):
        send_sms_task(MESSAGE, PHONE)

        self.send_sms.assert_called_once_with(MESSAGE, PHONE)

    @pytest.mark.parametrize(
        "error", [requests.ConnectionError("down"), requests.Timeout("slow")]
    )
    def test_network_error_is_retried_on_worker_fail(self, error):
        self.send_sms.side_effect = error

        result = send_sms_task.apply(args=(MESSAGE, PHONE))

        assert result.failed()
        assert isinstance(result.result, type(error))
        assert self.send_sms.call_count == 4  # first attempt + 3 retries

    def test_other_error_is_not_retried_fail(self):
        self.send_sms.side_effect = ValueError("bad number")

        result = send_sms_task.apply(args=(MESSAGE, PHONE))

        assert result.failed()
        assert isinstance(result.result, ValueError)
        assert self.send_sms.call_count == 1

    def test_inline_call_is_not_retried_fail(self):
        self.send_sms.side_effect = requests.ConnectionError("down")

        with pytest.raises(requests.ConnectionError):
            send_sms_task(MESSAGE, PHONE)

        assert self.send_sms.call_count == 1
