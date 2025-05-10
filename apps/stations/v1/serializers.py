from rest_framework import serializers

from apps.geo.v1.serializers import DistrictWithcitynameSerializer
from apps.stations.models.stations_models import (
    Service,
    Station,
    StationBranch,
    StationService,
)


class ListServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "unit", "type", "cost"]


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
    services = serializers.SerializerMethodField()
    district = DistrictWithcitynameSerializer()

    class Meta:
        model = Station
        fields = "__all__"

    def get_services(self, instance):
        services = Service.objects.filter(
            stationbranchservice__station_branch__station=instance
        ).values("id", "name")
        return list(services)


class StationNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ["id", "name"]


class SingleStationBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationBranch
        fields = ["id", "name", "address", "district", "station"]


class ListStationBranchSerializer(serializers.ModelSerializer):
    services = serializers.SerializerMethodField()
    district = DistrictWithcitynameSerializer()
    station = StationNameSerializer()
    managers_count = serializers.IntegerField()

    class Meta:
        model = StationBranch
        fields = "__all__"

    def get_services(self, instance):
        services = Service.objects.filter(
            stationbranchservice__station_branch=instance
        ).values("id", "name")
        return list(services)
