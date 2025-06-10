from rest_framework import serializers

from apps.companies.api.v1.serializers.car_serializer import CarWithPlateInfoSerializer
from apps.companies.api.v1.serializers.driver_serializer import SingleDriverSerializer
from apps.companies.models.company_models import Car, Driver
from apps.companies.models.operation_model import CarOperation
from apps.shared.base_exception_class import CustomValidationError
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
            "service_category",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
        return data

    def get_service_category(self, obj):
        if obj.service.type in [
            Service.ServiceType.PETROL,
            Service.ServiceType.DIESEL,
        ]:
            return "خدمات بترولية"
        return "خدمات أخرى"


class CreateCarOperationSerializer(serializers.ModelSerializer):
    car_code = serializers.CharField()
    driver_code = serializers.CharField()

    class Meta:
        model = CarOperation
        fields = ["start_time", "car_meter", "motor_image", "car_code", "driver_code"]

    def validate(self, attrs):
        car = Car.objects.filter(code=attrs["car_code"]).first()
        driver = Driver.objects.filter(code=attrs["driver_code"]).first()
        if not car:
            raise CustomValidationError({"car_code": "كود السيارة هذا غير صحيح"})
        if not driver:
            raise CustomValidationError({"driver_code": "كود السائق هذا غير صحيح"})
        if car.branch.company_id != driver.branch.company_id:
            raise CustomValidationError({"driver_code": "السائق لا ينتمي للشركة"})
        attrs["car"] = car
        attrs["driver"] = driver
        attrs["service"] = car.service
        attrs.pop("car_code")
        attrs.pop("driver_code")
        return attrs


class ListHomeCarOperationSerializer(serializers.ModelSerializer):
    car = CarWithPlateInfoSerializer()

    class Meta:
        model = CarOperation
        fields = ["id", "car", "start_time", "cost", "amount", "unit"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["unit"] = SERVICE_UNIT_CHOICES.get(data["unit"], data["unit"])
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
            "start_time",
            "end_time",
            "duration",
            "amount",
            "unit",
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
        return data

    def get_service_category(self, obj):
        if obj.service.type in [
            Service.ServiceType.PETROL,
            Service.ServiceType.DIESEL,
        ]:
            return "خدمات بترولية"
        return "خدمات أخرى"
