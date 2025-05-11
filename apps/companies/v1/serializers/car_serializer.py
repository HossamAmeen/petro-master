from rest_framework import serializers

from apps.companies.models.company_models import Car
from apps.companies.v1.serializers.branch_serializers import (
    SingleBranchWithDistrictSerializer,
)
from apps.shared.base_exception_class import CustomValidationError
from apps.utilities.serializers import BalanceUpdateSerializer

COLOR_CHOICES_HEX = {
    Car.PlateColor.RED: "#FF0000",
    Car.PlateColor.BLUE: "#0000FF",
    Car.PlateColor.ORANGE: "#FFA500",
    Car.PlateColor.YELLOW: "#FFFF00",
    Car.PlateColor.GREEN: "#008000",
    Car.PlateColor.GOLD: "#FFD700",
}


class ListCarSerializer(serializers.ModelSerializer):
    branch = SingleBranchWithDistrictSerializer()

    class Meta:
        model = Car
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["plate_color"] = COLOR_CHOICES_HEX.get(
            data["plate_color"], data["plate_color"]
        )
        return data


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = "__all__"

    def validate(self, attrs):
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

        return attrs


class CarWithPlateInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = ["id", "code", "plate_number", "plate_character", "plate_color"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["plate_color"] = COLOR_CHOICES_HEX.get(
            data["plate_color"], COLOR_CHOICES_HEX[Car.PlateColor.RED]
        )
        return data


class CarBalanceUpdateSerializer(BalanceUpdateSerializer):
    pass
