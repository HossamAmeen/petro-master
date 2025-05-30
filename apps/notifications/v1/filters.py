from django_filters import CharFilter
from django_filters.rest_framework import FilterSet

from apps.notifications.models import Notification


class NotificationFilter(FilterSet):
    type = CharFilter(
        field_name="type",
        lookup_expr="iexact",
        help_text=(
            f"""Filter by notification type({Notification.NotificationType.FUEL}, {Notification.NotificationType.MONEY}, {Notification.NotificationType.GENERAL}, {Notification.NotificationType.STATION_WORKER}, {Notification.NotificationType.STATION_SERVICE})"""
        ),
    )

    class Meta:
        model = Notification
        fields = ["is_read", "type"]
