from typing import override
from rest_framework import generics, mixins, views

from apps.notifications.models import Notification
from apps.notifications.serializers import (
    ListNotificationSerializer,
    NotificationSerializer,
)
from rest_framework import viewsets


class NotificationViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = Notification.objects.order_by('-id')

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ListNotificationSerializer
        return NotificationSerializer

