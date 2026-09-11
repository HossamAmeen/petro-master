import pytest

from apps.users.models import FirebaseToken

pytestmark = [pytest.mark.django_db]


class TestSignals:

    def test_create_notification_sends_fcm_with_user_tokens_success(
        self, mock_firebase_notifications, admin_user, notification_factory
    ):
        FirebaseToken.objects.create(user=admin_user, token="fcm-token-a")
        FirebaseToken.objects.create(user=admin_user, token="fcm-token-b")

        note = notification_factory(
            user=admin_user,
            title="Fuel done",
            description="Operation completed",
        )

        mock_firebase_notifications.assert_called_once()
        kwargs = mock_firebase_notifications.call_args.kwargs
        assert kwargs["title"] == "Fuel done"
        assert kwargs["body"] == "Operation completed"
        assert set(kwargs["device_tokens"]) == {"fcm-token-a", "fcm-token-b"}
        assert note.id

    def test_create_notification_without_tokens_still_sends_empty_list_success(
        self, mock_firebase_notifications, admin_user, notification_factory
    ):
        notification_factory(user=admin_user, title="No devices")

        mock_firebase_notifications.assert_called_once()
        assert mock_firebase_notifications.call_args.kwargs["device_tokens"] == []

    def test_update_notification_does_not_resend_fcm_success(
        self, mock_firebase_notifications, admin_user, notification_factory
    ):
        note = notification_factory(user=admin_user)
        mock_firebase_notifications.reset_mock()

        note.is_read = True
        note.save(update_fields=["is_read"])

        mock_firebase_notifications.assert_not_called()

    def test_create_notification_without_user_fail(self, notification_factory):
        with pytest.raises(AttributeError):
            notification_factory(user=None, title="Orphan")
