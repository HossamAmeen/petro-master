from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import SearchFilter

from apps.notifications.models import Notification
from apps.notifications.v1.filters import NotificationFilter
from apps.notifications.v1.serializers import (
    ListNotificationSerializer,
    NotificationSerializer,
)


class NotificationViewSet(
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    queryset = Notification.objects.order_by("-id")
    filterset_class = NotificationFilter
    filter_backends = [DjangoFilterBackend, SearchFilter]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-id")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListNotificationSerializer
        if self.request.method == "PATCH":
            return NotificationSerializer
