import math
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.accounting.helpers import (
    generate_company_transaction,
    generate_station_transaction,
)
from apps.accounting.models import KhaznaTransaction
from apps.companies.api.v1.serializers.car_serializer import CarWithPlateInfoSerializer
from apps.companies.api.v1.serializers.driver_serializer import SingleDriverSerializer
from apps.companies.models.operation_model import CarOperation
from apps.notifications.models import Notification
from apps.shared.constants import SERVICE_UNIT_CHOICES
from apps.stations.api.v1.serializers import (
    ServiceNameSerializer,
    SingleStationBranchSerializer,
)
from apps.stations.models.service_models import Service
from apps.users.models import CompanyUser, StationOwner, User
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
            "profits",
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


class CreateCarOperationSerializer(serializers.ModelSerializer):

    class Meta:
        model = CarOperation
        fields = "__all__"

    def validate(self, attrs):
        super().validate(attrs)
        # check service in station bramch service
        station_branch = attrs.get("station_branch")
        service = attrs.get("service")

        if service:
            if service not in station_branch.services.all():
                raise serializers.ValidationError("Service not found in station branch")
        car = attrs.get("car")
        if attrs.get("car_meter") < car.last_meter:
            raise serializers.ValidationError(
                "العداد الحالي يجب ان يكون اكبر من العداد السابق"
            )

        return attrs

    def create(self, validated_data):
        validated_data["status"] = CarOperation.OperationStatus.COMPLETED
        validated_data["start_time"] = timezone.localtime()
        validated_data["end_time"] = timezone.localtime() + timedelta(seconds=5)
        validated_data["duration"] = 5
        validated_data["unit"] = validated_data["service"].unit

        car = validated_data["car"]
        car_tank_capacity = (
            car.permitted_fuel_amount
            if car.permitted_fuel_amount
            else car.tank_capacity
        )
        service = validated_data["service"]
        company_liter_cost = service.cost * (car.branch.fees / 100) + service.cost
        available_liters = math.floor(car.balance / company_liter_cost)
        available_liters = min(car_tank_capacity, available_liters)
        if validated_data["amount"] > available_liters:
            raise serializers.ValidationError(
                {"error": "الكمية المطلوبة اكبر من الحد الأقصى"},
                code="not_found",
            )

        validated_data["cost"] = round(
            Decimal(validated_data["amount"]) * Decimal(service.cost),
            2,
        )
        validated_data["company_cost"] = round(
            Decimal(validated_data["amount"]) * Decimal(company_liter_cost),
            2,
        )
        worker = validated_data["worker"]
        validated_data["station_cost"] = round(
            Decimal(validated_data["amount"])
            * Decimal(service.cost + worker.station_branch.fees),
            2,
        )
        validated_data["profits"] = round(
            validated_data["company_cost"] - validated_data["station_cost"], 2
        )

        if car.is_with_odometer:
            car.fuel_consumption_rate = (
                validated_data["car_meter"] - car.last_meter
            ) / validated_data["amount"]

        validated_data["car_first_meter"] = (
            car.last_meter if car.last_meter > 0 else validated_data["car_meter"]
        )

        car.last_meter = validated_data["car_meter"]
        car.balance = car.balance - validated_data["company_cost"]
        car.save()
        request = self.context["request"]
        station_id = worker.station_branch.station_id
        generate_station_transaction(
            station_id=station_id,
            station_branch_id=worker.station_branch_id,
            amount=validated_data["station_cost"],
            status=KhaznaTransaction.TransactionStatus.APPROVED,
            description=f"تم تفويل سيارة رقم {car.plate} بعدد {validated_data['amount']} لتر",  # noqa
            created_by_id=worker.id,
            is_internal=False,
        )
        station_branch = worker.station_branch
        station_branch.balance = station_branch.balance - validated_data["station_cost"]
        station_branch.save()

        # send notifications for station users
        message = f"تم تفويل سيارة رقم {car.plate} بعدد {validated_data['amount']} لتر"  # noqa
        notification_users = []
        notification_users.extend(
            list(
                StationOwner.objects.filter(
                    station_id=station_id, role=StationOwner.UserRoles.StationOwner
                ).values_list("id", flat=True)
            )
        )
        notification_users.extend(
            list(
                StationOwner.objects.filter(
                    station_branch_id=worker.station_branch_id,
                    role=User.UserRoles.StationBranchManager,
                ).values_list("id", flat=True)
            )
        )
        notification_users.append(worker.id)

        for user_id in notification_users:
            Notification.objects.create(
                user_id=user_id,
                title=message,
                description=message,
                type=Notification.NotificationType.MONEY,
            )

        # send notfication for company user
        company_id = car.branch.company_id
        generate_company_transaction(
            company_id=company_id,
            amount=validated_data["company_cost"],
            status=KhaznaTransaction.TransactionStatus.APPROVED,
            description=f"تم تفويل سيارة رقم {car.plate} بعدد {validated_data['amount']} لتر",  # noqa
            created_by_id=request.user.id,
            is_internal=True,
        )
        message = (
            f"تم تفويل سيارة رقم {car.plate} بعدد {validated_data['amount']} لتر "  # noqa
            f"وخصم مبلغ بمقدار {validated_data['company_cost']:.2f} جنية"  # noqa
        )
        notification_users = list(
            CompanyUser.objects.filter(
                company_id=company_id, role=CompanyUser.UserRoles.CompanyOwner
            ).values_list("id", flat=True)
        )
        notification_users.extend(
            list(
                CompanyUser.objects.filter(
                    company_id=company_id,
                    role=CompanyUser.UserRoles.CompanyBranchManager,
                ).values_list("id", flat=True)
            )
        )
        notification_users.append(request.user.id)
        for user_id in notification_users:
            Notification.objects.create(
                user_id=user_id,
                title=message,
                description=message,
                type=Notification.NotificationType.MONEY,
            )

        return super().create(validated_data)
