from unittest.mock import MagicMock, patch

import pytest

from apps.notifications.tests.conftest import ORIGINAL_SEND_FCM


pytestmark = [pytest.mark.django_db]


@patch("apps.notifications.fcm_manager.messaging.send_each")
@patch("apps.notifications.fcm_manager.messaging.Message")
@patch("apps.notifications.fcm_manager.messaging.Notification")
def test_send_fcm_message_sends_one_message_per_token_success(
    mock_notification, mock_message, mock_send_each
):
    response = MagicMock()
    first = MagicMock(success=True)
    second = MagicMock(success=False)
    response.responses = [first, second]
    mock_send_each.return_value = response

    result = ORIGINAL_SEND_FCM("Hello", "Body", ["token-1", "token-2"])

    assert mock_message.call_count == 2
    mock_send_each.assert_called_once()
    sent_messages = mock_send_each.call_args[0][0]
    assert len(sent_messages) == 2
    assert result is response


@patch("apps.notifications.fcm_manager.messaging.send_each")
@patch("apps.notifications.fcm_manager.messaging.Message")
@patch("apps.notifications.fcm_manager.messaging.Notification")
def test_send_fcm_message_empty_tokens_success(
    mock_notification, mock_message, mock_send_each
):
    mock_send_each.return_value = MagicMock(responses=[])

    result = ORIGINAL_SEND_FCM("Hello", "Body", [])

    mock_message.assert_not_called()
    mock_send_each.assert_called_once_with([])
    assert result is mock_send_each.return_value


@patch("apps.notifications.fcm_manager.messaging.send_each")
@patch("apps.notifications.fcm_manager.messaging.Message")
@patch("apps.notifications.fcm_manager.messaging.Notification")
def test_send_fcm_message_exception_returns_none_fail(
    mock_notification, mock_message, mock_send_each
):
    mock_send_each.side_effect = Exception("firebase down")

    result = ORIGINAL_SEND_FCM("Hello", "Body", ["token-1"])

    assert result is None
