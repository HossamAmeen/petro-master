from rest_framework import serializers

from apps.companies.api.v1.serializers.car_serializer import CarWithPlateInfoSerializer
from apps.companies.api.v1.serializers.driver_serializer import SingleDriverSerializer
from apps.companies.models.operation_model import CarOperation
from apps.shared.constants import SERVICE_UNIT_CHOICES
from apps.stations.api.v1.serializers import (
    ServiceNameSerializer,
    SingleStationBranchSerializer,
)
from apps.stations.models.service_models import Service
from apps.users.v1.serializers.station_serializer import WorkerWithBranchSerializer


class ListCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()
    driver = SingleDriverSerializer()
    station_branch = SingleStationBranchSerializer()
    worker = WorkerWithBranchSerializer()
    service = ServiceNameSerializer()
    service_category = serializers.SerializerMethodField()

    class Meta:
        model = CarOperation
        fields = [
            "id",
            "code",
            "status",
            "start_time",
            "end_time",
            "created",
            "duration",
            "cost",
            "company_cost",
            "station_cost",
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
            "service_category",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
        data["duration"] = instance.duration / 60
        data["cost"] = (
            float(instance.company_cost) if instance.company_cost else 0
        )  # should be deleted
        data["company_cost"] = (
            float(instance.company_cost) if instance.company_cost else 0
        )  # should be deleted
        data["amount"] = (
            float(instance.amount) if instance.amount else 0
        )  # should be deleted
        return data

    def get_service_category(self, obj):
        if obj.service and obj.service.type in [
            Service.ServiceType.PETROL,
            Service.ServiceType.DIESEL,
        ]:
            return "خدمات بترولية"
        return "خدمات أخرى"


class ListCompanyHomeCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        model = CarOperation
        fields = [
            "id",
            "car",
            "start_time",
            "cost",
            "company_cost",
            "amount",
            "unit",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
        data["cost"] = (
            float(instance.company_cost) if instance.company_cost else 0
        )  # should be deleted
        data["company_cost"] = (
            float(instance.company_cost) if instance.company_cost else 0
        )  # should be deleted
        data["amount"] = (
            float(instance.amount) if instance.amount else 0
        )  # should be deleted
        return data


class ListStationCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()
    worker = WorkerWithBranchSerializer()
    service = ServiceNameSerializer()
    company_name = serializers.CharField(source="driver.branch.company.name")
    service_category = serializers.SerializerMethodField()

    class Meta:
        model = CarOperation
        fields = [
            "id",
            "car",
            "cost",
            "station_cost",
            "start_time",
            "end_time",
            "created",
            "duration",
            "amount",
            "unit",
            "status",
            "service",
            "service_category",
            "worker",
            "driver",
            "company_name",
            "motor_image",
            "fuel_image",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["cost"] = instance.station_cost if instance.station_cost else 0
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
        data["duration"] = instance.duration / 60
        data["station_cost"] = instance.station_cost if instance.station_cost else 0
        data["amount"] = instance.amount if instance.amount else 0
        return data

    def get_service_category(self, obj):
        if obj.service and obj.service.type in [
            Service.ServiceType.PETROL,
            Service.ServiceType.DIESEL,
        ]:
            return "خدمات بترولية"
        return "خدمات أخرى"
