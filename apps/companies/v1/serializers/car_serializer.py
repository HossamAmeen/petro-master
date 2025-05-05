from rest_framework import serializers

from apps.companies.models.company_models import Car
from apps.companies.v1.serializers.branch_serializers import (
    SingleBranchWithDistrictSerializer,
)
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
