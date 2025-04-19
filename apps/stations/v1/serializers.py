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
    services = ServiceNameSerializer(source="station_services__service", many=True)
    district = DistrictWithcitynameSerializer()

    class Meta:
        model = Station
        fields = "__all__"

    def get_services(self, instance):
        # Directly query Service objects through the StationService relationship
        services = Service.objects.filter(station_service__station=instance).values(
            "id", "name"
        )
        return list(services)
