import math

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
            "profit",
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
        data["duration"] = math.ceil(instance.duration / 60)
        return data

    def get_service_category(self, obj):
        if obj.service and obj.service.type in [
            Service.ServiceType.PETROL,
            Service.ServiceType.DIESEL,
        ]:
            return "خدمات بترولية"
        return "خدمات أخرى"


class ListCompanyCarOperationSerializer(ListCarOperationSerializer):
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
        data["duration"] = math.ceil(instance.duration / 60)
        return data

    def get_service_category(self, obj):
        if obj.service and obj.service.type in [
            Service.ServiceType.PETROL,
            Service.ServiceType.DIESEL,
        ]:
            return "خدمات بترولية"
        return "خدمات أخرى"


class SingleCarOperationSerializer(ListCarOperationSerializer):
    pass


class ListCompanyHomeCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()

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
        return data


class ListStationCarOperationSerializer(serializers.ModelSerializer):
    car = serializers.SerializerMethodField()
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
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
        data["duration"] = math.ceil(instance.duration / 60)
        return data

    def get_service_category(self, obj):
        if obj.service and obj.service.type in [
            Service.ServiceType.PETROL,
            Service.ServiceType.DIESEL,
        ]:
            return "خدمات بترولية"
        return "خدمات أخرى"

    def get_car(self, obj):
        car = obj.car
        company_branch = car.branch
        if obj.service:
            liter_cost = (
                obj.service.cost * company_branch.fees / 100
            ) + obj.service.cost

            liters_count = (
                car.permitted_fuel_amount
                if car.permitted_fuel_amount
                else car.tank_capacity
            )
            available_liters = math.floor(car.balance / liter_cost)
            available_liters = min(liters_count, available_liters)
        else:
            available_liters = 0
            liter_cost = 0

        return {
            "plate_number": car.plate_number,
            "plate_character": car.plate_character,
            "plate_color": car.plate_color,
            "fuel_type": car.fuel_type,
            "liter_count": available_liters,
            "cost": available_liters * liter_cost,
            "code": obj.code,
            "id": obj.id,
        }
