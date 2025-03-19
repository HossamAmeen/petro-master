from rest_framework import viewsets

from apps.stations.models import Station
from apps.stations.serializers import StationSerializer


class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
