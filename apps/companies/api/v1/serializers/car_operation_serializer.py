from rest_framework import serializers

from apps.companies.api.v1.serializers.car_serializer import CarWithPlateInfoSerializer
from apps.companies.api.v1.serializers.driver_serializer import SingleDriverSerializer
from apps.companies.models.operation_model import CarOperation
from apps.shared.constants import SERVICE_UNIT_CHOICES
from apps.stations.v1.serializers import (
    ServiceNameSerializer,
    SingleStationBranchSerializer,
)
from apps.users.v1.serializers.station_serializer import SingleWorkerSerializer


class ListCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()
    driver = SingleDriverSerializer()
    station_branch = SingleStationBranchSerializer()
    worker = SingleWorkerSerializer()
    service = ServiceNameSerializer()

    class Meta:
        model = CarOperation
        fields = [
            "id",
            "code",
            "status",
            "start_time",
            "end_time",
            "duration",
            "cost",
            "amount",
            "unit",
            "fuel_type",
            "car",
            "driver",
            "station_branch",
            "worker",
            "service",
            "car_meter",
            "motor_image",
            "fuel_image",
            "fuel_consumption_rate",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
        return data


class ListHomeCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()

    class Meta:
        model = CarOperation
        fields = ["id", "car", "start_time", "cost", "amount", "unit"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
        return data
