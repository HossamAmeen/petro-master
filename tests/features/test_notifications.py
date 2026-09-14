"""A money action notifies users in-app and pushes to their registered devices.

Each test follows the Given-When-Then template; the funded company, the two
signed-in clients and their registered FCM devices live in ``setup``.
"""

import pytest
from rest_framework import status

from apps.companies.tests.api.v1.car.helpers import update_balance_url
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification
from apps.notifications.tests.helpers import (
    notifications_detail_url,
    notifications_list_url,
)
from apps.users.tests.helpers import (
    firebase_tokens_delete_by_token_url,
    firebase_tokens_list_url,
)

from .helpers import sign_in

pytestmark = [pytest.mark.django_db, pytest.mark.feature]


def pushed_tokens(fcm_mock):
    return sorted(
        tuple(call.kwargs["device_tokens"]) for call in fcm_mock.call_args_list
    )


class TestNotifications:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        mock_firebase_notifications,
        company,
        company_owner,
        company_branch_manager,
        fuelable_car,
    ):
        self.fcm = mock_firebase_notifications
        self.owner_user = company_owner
        self.car = fuelable_car
        set_balance(company, "100.00")
        self.owner = sign_in("company", company_owner)
        self.manager = sign_in("company", company_branch_manager)
        self.owner.post(firebase_tokens_list_url(), {"token": "owner-device"})
        self.manager.post(firebase_tokens_list_url(), {"token": "manager-device"})

    def top_up_car(self):
        return self.owner.post(
            update_balance_url(self.car.id),
            {"amount": "40.00", "type": "add"},
            format="json",
        )

    def test_top_up_notifies_and_pushes_to_devices_success(self):
        # Given both users have a registered device (from setup)
        self.fcm.reset_mock()

        # When the owner tops up the car (a MONEY action)
        topped_up = self.top_up_car()
        listed = self.owner.get(notifications_list_url())

        # Then FCM is pushed to both devices and the in-app row is unread
        assert topped_up.status_code == status.HTTP_200_OK, topped_up.data
        assert pushed_tokens(self.fcm) == [("manager-device",), ("owner-device",)]
        (notification,) = listed.data["results"]
        assert notification["type"] == Notification.NotificationType.MONEY
        assert notification["is_read"] is False
        # company and station roles always get 0; only dashboard roles count
        assert listed.data["unread_count"] == 0

    def test_user_marks_a_notification_read_success(self):
        # Given an unread notification from a top-up
        self.top_up_car()
        notification = Notification.objects.get(user=self.owner_user)

        # When the owner marks it read
        marked = self.owner.patch(
            notifications_detail_url(notification.id), {"is_read": True}, format="json"
        )
        unread = self.owner.get(notifications_list_url(is_read="false"))

        # Then it no longer appears in the unread list
        assert marked.status_code == status.HTTP_200_OK, marked.data
        assert unread.data["results"] == []

    def test_removed_device_gets_no_push_success(self):
        # Given the owner has removed their device
        removed = self.owner.delete(
            firebase_tokens_delete_by_token_url(),
            {"token": "owner-device"},
            format="json",
        )
        self.fcm.reset_mock()

        # When a MONEY action fires
        self.top_up_car()

        # Then only the manager's device is pushed to
        assert removed.status_code == status.HTTP_204_NO_CONTENT
        assert pushed_tokens(self.fcm) == [(), ("manager-device",)]

    def test_cannot_read_or_mark_someone_elses_notification_fail(self):
        # Given a notification that belongs to the owner
        self.top_up_car()
        notification = Notification.objects.get(user=self.owner_user)
        manager_ids = {
            item["id"]
            for item in self.manager.get(notifications_list_url()).data["results"]
        }

        # When the manager tries to mark it read
        response = self.manager.patch(
            notifications_detail_url(notification.id), {"is_read": True}, format="json"
        )

        # Then it is not visible to them and the PATCH 404s
        assert notification.id not in manager_ids
        assert response.status_code == status.HTTP_404_NOT_FOUND
        notification.refresh_from_db()
        assert notification.is_read is False
