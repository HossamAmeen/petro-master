from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.v1.filters import NotificationFilter
from apps.notifications.v1.serializers import (
    ListNotificationSerializer,
    NotificationSerializer,
)
from apps.shared.constants import DASHBOARD_ROLES


class NotificationViewSet(
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    queryset = Notification.objects.order_by("-id")
    filterset_class = NotificationFilter
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ["title", "description"]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by("-id")

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ListNotificationSerializer
        if self.request.method == "PATCH":
            return NotificationSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        unread_count = 0
        # Get unread count for dashboard users
        if request.user.role in DASHBOARD_ROLES:
            unread_count = Notification.objects.filter(
                user=request.user, is_read=False
            ).count()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["unread_count"] = unread_count
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "unread_count": unread_count})
