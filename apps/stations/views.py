from rest_framework import viewsets

from apps.stations.models.stations_models import Station
from apps.stations.v1.serializers import StationSerializer


class StationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Station.objects.prefetch_related("services").order_by("-id")
    serializer_class = StationSerializer
