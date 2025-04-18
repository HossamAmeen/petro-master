from rest_framework import serializers

from apps.geo.v1.serializers import DistrictWithcitynameSerializer
from apps.stations.models.stations_models import Station, StationService


class SingleStationServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationService
        fields = ["id", "service"]


class ListStationSerializer(serializers.ModelSerializer):
    services = SingleStationServiceSerializer(source="station_services", many=True)
    district = DistrictWithcitynameSerializer()

    class Meta:
        model = Station
        fields = "__all__"
