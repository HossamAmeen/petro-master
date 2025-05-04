from rest_framework import serializers

from apps.companies.models.company_models import Company
from apps.companies.models.operation_model import CarOperation
from apps.geo.v1.serializers import ListDistrictSerializer


class ListCompanySerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()

    class Meta:
        model = Company
        fields = "__all__"


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class CompanyNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["name"]


class CompanyHomeSerializer(serializers.ModelSerializer):
    total_cars_count = serializers.IntegerField()
    diesel_cars_count = serializers.IntegerField()
    gasoline_cars_count = serializers.IntegerField()
    total_drivers_count = serializers.IntegerField()
    total_drivers_with_lincense_expiration_date = serializers.IntegerField()
    total_drivers_with_lincense_expiration_date_30_days = serializers.IntegerField()
    total_branches_count = serializers.IntegerField()
    cars_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    branches_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Company
        fields = [
            "name",
            "total_cars_count",
            "diesel_cars_count",
            "gasoline_cars_count",
            "total_drivers_count",
            "total_drivers_with_lincense_expiration_date",
            "total_drivers_with_lincense_expiration_date_30_days",
            "total_branches_count",
            "balance",
            "cars_balance",
            "branches_balance",
            "total_balance",
        ]

    def to_representation(self, instance):
        from apps.companies.v1.serializers.car_operation_serializer import (
            ListHomeCarOperationSerializer,
        )

        data = super().to_representation(instance)
        data["car_operations"] = ListHomeCarOperationSerializer(
            CarOperation.objects.filter(car__branch__company=instance).order_by("-id")[
                :3
            ],
            many=True,
        ).data
        return data
