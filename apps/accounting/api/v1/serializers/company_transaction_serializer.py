from rest_framework import serializers

from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)
from apps.shared.generate_code import generate_unique_code
from apps.stations.api.v1.serializers import StationBranchWithDistrictSerializer


class ListCompanyKhaznaTransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyKhaznaTransaction
        fields = "__all__"


class ListCompanyKhaznaTransactionForDashboardSerializer(serializers.ModelSerializer):
    company_branch_name = serializers.SerializerMethodField()

    class Meta:
        model = CompanyKhaznaTransaction
        fields = "__all__"

    def get_company_branch_name(self, obj):
        return obj.company_branch.name if obj.company_branch else None


class CreateCompanyKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyKhaznaTransaction
        fields = "__all__"


class StationKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationKhaznaTransaction
        fields = "__all__"


class KhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KhaznaTransaction
        fields = "__all__"


class CreateStationKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationKhaznaTransaction
        exclude = ("created_by", "updated_by", "reference_code")

    def create(self, validated_data):
        validated_data["reference_code"] = generate_unique_code(
            model=StationKhaznaTransaction,
            look_up="reference_code",
            min_value=10**8,
            max_value=10**9,
        )
        return super().create(validated_data)


class ListStationKhaznaTransactionSerializer(serializers.ModelSerializer):
    station_branch = StationBranchWithDistrictSerializer(read_only=True)

    class Meta:
        model = StationKhaznaTransaction
        fields = "__all__"
