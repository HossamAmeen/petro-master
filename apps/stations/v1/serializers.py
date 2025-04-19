from rest_framework import serializers

from apps.geo.v1.serializers import DistrictWithcitynameSerializer
from apps.stations.models.stations_models import Service, Station, StationService


class ServiceNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Service
        fields = ["id", "name"]


class SingleStationServiceSerializer(serializers.ModelSerializer):
    service = ServiceNameSerializer()

    class Meta:
        model = StationService
        fields = ["id", "service"]


class ListStationSerializer(serializers.ModelSerializer):
    services = SingleStationServiceSerializer(source="station_services", many=True)
    district = DistrictWithcitynameSerializer()

    class Meta:
        model = Station
        fields = "__all__"
