from rest_framework import serializers

from apps.companies.models.operation_model import CarOperation
from apps.shared.base_exception_class import CustomValidationError
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import StationBranchService


class updateStationGasCarOperationSerializer(serializers.Serializer):
    car_meter = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    motor_image = serializers.ImageField(required=False)
    fuel_image = serializers.ImageField(required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    start_time = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if "amount" in attrs and attrs["amount"] <= 0:
            raise CustomValidationError({"amount": "الكمية يجب ان تكون اكبر من 0"})
        if "car_meter" in attrs:
            if "motor_image" not in attrs:
                raise CustomValidationError(
                    {"motor_image": "يجب ارفاق صورة لعداد السيارة"}
                )
            if attrs["car_meter"] < 0:
                raise CustomValidationError(
                    {"car_meter": "يجب ان يكون العداد اكبر من 0"}
                )
        if "amount" in attrs and "fuel_image" not in attrs:
            raise CustomValidationError({"fuel_image": "يجب ارفاق صورة لمضخه الوقود"})
        return attrs

    def update(self, instance, validated_data):
        instance.car_meter = validated_data.get("car_meter", instance.car_meter)
        instance.motor_image = validated_data.get("motor_image", instance.motor_image)
        instance.fuel_image = validated_data.get("fuel_image", instance.fuel_image)
        instance.amount = validated_data.get("amount", instance.amount)
        instance.status = validated_data.get("status", instance.status)
        instance.unit = validated_data.get("unit", instance.unit)
        instance.duration = validated_data.get("duration", instance.duration)
        instance.end_time = validated_data.get("end_time", instance.end_time)
        instance.cost = validated_data.get("cost", instance.cost)
        instance.company_cost = validated_data.get(
            "company_cost", instance.company_cost
        )
        instance.station_cost = validated_data.get(
            "station_cost", instance.station_cost
        )
        instance.profits = validated_data.get("profits", instance.profits)
        instance.save()

        return instance


class updateStationOtherCarOperationSerializer(serializers.ModelSerializer):
    service = serializers.IntegerField(required=True)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    car_image = serializers.ImageField(required=True)

    class Meta:
        model = CarOperation
        fields = ["service", "cost", "car_image"]

    def __init__(self, *args, **kwargs):
        self.service_name = None
        super().__init__(*args, **kwargs)

    def validate_cost(self, cost):
        if cost <= 0:
            raise CustomValidationError({"cost": "السعر يجب ان يكون اكبر من 0"})
        return cost

    def validate_service(self, service):
        station_branch = self.context["station_branch_id"]
        branch_service = (
            StationBranchService.objects.select_related("service")
            .filter(service=service, station_branch=station_branch)
            .first()
        )
        if not branch_service:
            raise CustomValidationError({"service": "الخدمة غير متاح للفرع الخاص بكم"})
        self.service_name = branch_service.service.name
        return branch_service.service

    def update(self, instance, validated_data):
        instance.service_id = validated_data.get("service", instance.service)
        instance.cost = validated_data.get("cost", instance.cost)
        instance.car_image = validated_data.get("car_image", instance.car_image)
        instance.unit = (Service.ServiceUnit.UNIT,)
        instance.status = validated_data.get("status", instance.status)
        instance.save()

        return instance

    def to_representation(self, instance):
        return {"service_name": self.service_name}
