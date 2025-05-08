from rest_framework import viewsets

from apps.stations.models.stations_models import Station, StationBranch
from apps.stations.v1.serializers import (
    ListStationBranchSerializer,
    ListStationSerializer,
)
from apps.users.models import User


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.prefetch_related("station_services").order_by("-id")
    serializer_class = ListStationSerializer


class StationBranchViewSet(viewsets.ModelViewSet):
    queryset = StationBranch.objects.prefetch_related(
        "station_branch_services"
    ).order_by("-id")
    serializer_class = ListStationBranchSerializer

    def get_queryset(self):
        if self.request.user.role == User.UserRoles.StationOwner:
            return self.queryset.filter(station__owners=self.request.user)
        if self.request.user.role == User.UserRoles.CompanyBranchManager:
            return self.queryset.filter(station__company=self.request.company_id)
        return self.queryset.distinct()
