from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.shared.mixins.inject_user_mixins import InjectUserMixin
from apps.shared.permissions import AdminPermission
from apps.users.models import Supervisor
from apps.users.v1.serializers.agent_serializer import (
    CreateSupervisorSerializer,
    ListSupervisorSerializer,
)


class SupervisorViewSet(InjectUserMixin, viewsets.ModelViewSet):
    queryset = (
        Supervisor.objects.order_by("-id")
        .select_related("created_by", "updated_by")
        .prefetch_related("district")
    )
    serializer_class = ListSupervisorSerializer
    permission_classes = [IsAuthenticated, AdminPermission]

    def get_serializer_class(self):
        if self.request.method == "POST" or self.request.method == "PATCH":
            return CreateSupervisorSerializer
        return ListSupervisorSerializer
