from rest_framework import viewsets

from apps.stations.models.stations_models import Station, StationBranch
from apps.stations.v1.serializers import (
    ListStationBranchSerializer,
    ListStationSerializer,
)


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.prefetch_related("station_services").order_by("-id")
    serializer_class = ListStationSerializer


class StationBranchViewSet(viewsets.ModelViewSet):
    queryset = StationBranch.objects.prefetch_related(
        "station_branch_services"
    ).order_by("-id")
    serializer_class = ListStationBranchSerializer
