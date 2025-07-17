from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.companies.api.v1.serializers.branch_serializers import (
    SingleBranchWithDistrictSerializer,
)
from apps.companies.models.company_models import Car, CarCode
from apps.shared.base_exception_class import CustomValidationError
from apps.stations.api.v1.serializers import ServiceNameSerializer
from apps.utilities.serializers import BalanceUpdateSerializer

FUEL_TYPE_CHOICES = {
    Car.FuelType.DIESEL: "ديزل",
    Car.FuelType.SOLAR: "سولار",
    Car.FuelType.GASOLINE: "بنزين",
    Car.FuelType.ELECTRIC: "كهرباء",
    Car.FuelType.NATURAL_GAS: "غاز طبيعي",
}


class ListCarSerializer(serializers.ModelSerializer):
    service = ServiceNameSerializer()
    backup_service = ServiceNameSerializer()
    branch = SingleBranchWithDistrictSerializer()
    is_license_expiring_soon = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="branch.company.name")

    class Meta:
        model = Car
        fields = "__all__"

    def get_is_license_expiring_soon(self, obj):
        if obj.license_expiration_date:
            expiry_date = obj.license_expiration_date
            time_difference = expiry_date - timezone.localtime().date()
            return time_difference <= timedelta(days=30)
        return False

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["fuel_type"] = FUEL_TYPE_CHOICES.get(data["fuel_type"], data["fuel_type"])
        return data


class CarSerializer(serializers.ModelSerializer):

    class Meta:
        model = Car
        fields = "__all__"

    def validate(self, attrs):
        super().validate(attrs)
        permitted_fuel_amount = attrs.get(
            "permitted_fuel_amount",
            getattr(self.instance, "permitted_fuel_amount", None),
        )
        tank_capacity = attrs.get(
            "tank_capacity", getattr(self.instance, "tank_capacity", None)
        )
        if permitted_fuel_amount is not None and tank_capacity is not None:
            if permitted_fuel_amount > tank_capacity:
                raise CustomValidationError(
                    message="الكمية المسموح بها أكبر من حجم المخزون",
                    code="invalid",
                    errors=[],
                )
        if attrs.get("service") and attrs.get("backup_service"):
            if attrs.get("service") == attrs.get("backup_service"):
                raise CustomValidationError(
                    message="لا يمكن أن يكون الخدمة الرئيسية والنسخة الاحتياطية نفس الخدمة",
                    code="invalid",
                    errors=[],
                )
        if attrs.get("code"):
            if not CarCode.objects.filter(code=attrs["code"]).exists():
                raise CustomValidationError(
                    message="رقم الكود غير موجود في السستم",
                    code="invalid",
                    errors=[],
                )
            existing_car = Car.objects.filter(code=attrs["code"])
            if self.instance:
                existing_car = existing_car.exclude(id=self.instance.id)
            if existing_car.exists():
                raise CustomValidationError(
                    message="رقم السيارة موجود بالفعل",
                    code="invalid",
                    errors=[],
                )

        return attrs


class CarCreationSerializer(CarSerializer):
    pass


class CarWithPlateInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ["id", "code", "plate_number", "plate_character", "plate_color"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data


class CarBalanceUpdateSerializer(BalanceUpdateSerializer):
    pass


class RetrieveCarWithCompanySerializer(serializers.ModelSerializer):
    company = serializers.CharField(source="branch.company.name")

    class Meta:
        model = Car
        fields = [
            "id",
            "code",
            "plate_number",
            "plate_character",
            "plate_color",
            "company",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        return data
