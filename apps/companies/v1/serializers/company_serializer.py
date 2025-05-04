from django.db.models import Sum
from rest_framework import serializers

from apps.companies.models.company_models import Company
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
    total_cars = serializers.IntegerField()
    total_drivers = serializers.IntegerField()
    total_branches = serializers.IntegerField()
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Company
        fields = ["name"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["total_cars"] = instance.cars.count()
        data["total_drivers"] = instance.drivers.count()
        data["total_branches"] = instance.branches.count()
        data["cars_balance"] = instance.cars.values("balance").aggregate(
            total_balance=Sum("balance")
        )["total_balance"]
        data["branches_balance"] = instance.branches.values("balance").aggregate(
            total_balance=Sum("balance")
        )["total_balance"]
        data["total_balance"] = (
            instance.balance + data["cars_balance"] + data["branches_balance"]
        )
        return data
