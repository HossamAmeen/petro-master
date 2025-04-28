from rest_framework import serializers

from apps.companies.models.operation_model import CarOperation
from apps.companies.v1.serializers.branch_serializers import (
    SingleBranchWithDistrictSerializer,
)
from apps.companies.v1.serializers.car_serializer import CarWithPlateInfoSerializer
from apps.companies.v1.serializers.driver_serializer import SingleDriverSerializer
from apps.stations.v1.serializers import SingleStationServiceSerializer
from apps.users.v1.serializers.station_serializer import SingleWorkerSerializer


class listCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()
    driver = SingleDriverSerializer()
    station_branch = SingleBranchWithDistrictSerializer()
    worker = SingleWorkerSerializer()
    service = SingleStationServiceSerializer()

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
        ]
