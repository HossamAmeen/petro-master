import pytest
from rest_framework import status

from apps.notifications.models import Notification
from apps.notifications.tests.helpers import (
    notifications_detail_url,
    notifications_list_url,
)


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_update_without_authentication_fail(api_client, admin_user, notification_factory):
    note = notification_factory(user=admin_user)

    response = api_client.patch(
        notifications_detail_url(note.id),
        {"is_read": True},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    note.refresh_from_db()
    assert note.is_read is False


def test_update_marks_read_success(auth_client, admin_user, notification_factory):
    note = notification_factory(user=admin_user, is_read=False)

    response = auth_client(admin_user).patch(
        notifications_detail_url(note.id),
        {"is_read": True},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    assert response.data == {"is_read": True}
    note.refresh_from_db()
    assert note.is_read is True


def test_update_ignores_title_and_type_success(
    auth_client, admin_user, notification_factory
):
    note = notification_factory(
        user=admin_user,
        title="Original",
        type=Notification.NotificationType.GENERAL,
        is_read=False,
    )

    response = auth_client(admin_user).patch(
        notifications_detail_url(note.id),
        {
            "is_read": True,
            "title": "Hacked",
            "type": Notification.NotificationType.FUEL,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    note.refresh_from_db()
    assert note.is_read is True
    assert note.title == "Original"
    assert note.type == Notification.NotificationType.GENERAL


def test_update_other_users_notification_fail(
    auth_client, admin_user, finance_user, notification_factory
):
    note = notification_factory(user=finance_user, is_read=False)

    response = auth_client(admin_user).patch(
        notifications_detail_url(note.id),
        {"is_read": True},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    note.refresh_from_db()
    assert note.is_read is False


def test_update_unknown_notification_fail(auth_client, admin_user):
    response = auth_client(admin_user).patch(
        notifications_detail_url(999_999),
        {"is_read": True},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_update_decreases_dashboard_unread_count_success(
    auth_client, admin_user, notification_factory
):
    note = notification_factory(user=admin_user, is_read=False)
    notification_factory(user=admin_user, is_read=False)

    auth_client(admin_user).patch(
        notifications_detail_url(note.id),
        {"is_read": True},
        format="json",
    )
    response = auth_client(admin_user).get(notifications_list_url(no_paginate="true"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["unread_count"] == 1


def test_retrieve_method_not_allowed_fail(
    auth_client, admin_user, notification_factory
):
    note = notification_factory(user=admin_user)

    response = auth_client(admin_user).get(notifications_detail_url(note.id))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_delete_method_not_allowed_fail(
    auth_client, admin_user, notification_factory
):
    note = notification_factory(user=admin_user)

    response = auth_client(admin_user).delete(notifications_detail_url(note.id))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert Notification.objects.filter(pk=note.id).exists()
