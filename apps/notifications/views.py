from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.notifications.models import Notification
from apps.notifications.serializers import (
    ListNotificationSerializer,
    NotificationSerializer,
)


class NotificationViewSet(ReadOnlyModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListNotificationSerializer
        return NotificationSerializer
