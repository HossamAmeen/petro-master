from rest_framework import viewsets

from apps.stations.models.stations_models import Station, StationBranch
from apps.stations.v1.serializers import ListStationSerializer


class StationViewSet(viewsets.ModelViewSet):
    permission_classes = []
    authentication_classes = []
    queryset = Station.objects.prefetch_related("station_services").order_by("-id")
    serializer_class = ListStationSerializer


class StationBranchViewSet(viewsets.ModelViewSet):
    queryset = StationBranch.objects.all()
    serializer_class = ListStationSerializer
