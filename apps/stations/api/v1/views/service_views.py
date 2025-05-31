from rest_framework import viewsets

from apps.stations.api.v1.serializers import ListServiceSerializer
from apps.stations.filters import ServiceFilter
from apps.stations.models.service_models import Service
from apps.users.models import User


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all().order_by("-id")
    serializer_class = ListServiceSerializer
    filterset_class = ServiceFilter

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.exclude(
                station_branch_services__station_branch__station_id=self.request.station_id
            )
        if self.request.user.role == User.UserRoles.StationBranchManager:
            return self.queryset.exclude(
                station_branch_services__station_branch__station__managers__user=self.request.user
            )
        return self.queryset.distinct()
