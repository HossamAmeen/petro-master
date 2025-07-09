from rest_framework import serializers

from apps.accounting.api.v1.serializers.company_transaction_serializer import (
    ListCompanyKhaznaTransactionSerializer,
)
from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.models.company_models import Company
from apps.geo.v1.serializers import ListDistrictSerializer


class ListCompanySerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()

    class Meta:
        model = Company
        fields = "__all__"


class ListCompanyNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Company
        fields = ["id", "name"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class CompanyNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name"]


class CompanyWalletSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    cars_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    branches_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cars_count = serializers.IntegerField()
    total_drivers_count = serializers.IntegerField()
    total_branches_count = serializers.IntegerField()

    class Meta:
        model = Company
        fields = [
            "balance",
            "cars_balance",
            "branches_balance",
            "total_balance",
            "total_cars_count",
            "total_drivers_count",
            "total_branches_count",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["company_transactions"] = ListCompanyKhaznaTransactionSerializer(
            CompanyKhaznaTransaction.objects.filter(company=instance).order_by("-id")[
                :3
            ],
            many=True,
        ).data
        return data
