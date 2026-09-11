import pytest

from apps.notifications.fcm_manager import FCMManager
from apps.notifications.models import Notification

# Captured at import time, before the autouse FCM mock replaces the class attribute.
ORIGINAL_SEND_FCM = FCMManager.send_fcm_message


@pytest.fixture
def notification_factory(db):
    counter = {"n": 0}

    def create_notification(**overrides):
        counter["n"] += 1
        defaults = {
            "title": f"Notification {counter['n']}",
            "description": f"Description {counter['n']}",
            "type": Notification.NotificationType.GENERAL,
            "is_read": False,
            "is_success": True,
        }
        defaults.update(overrides)
        return Notification.objects.create(**defaults)

    return create_notification
