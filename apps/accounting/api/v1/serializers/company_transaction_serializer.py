from rest_framework import serializers

from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)
from apps.stations.api.v1.serializers import SingleStationBranchSerializer


class ListCompanyKhaznaTransactionSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source="get_status_display", read_only=True)

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


class ListStationKhaznaTransactionSerializer(serializers.ModelSerializer):
    station_branch = SingleStationBranchSerializer(read_only=True)

    class Meta:
        model = StationKhaznaTransaction
        fields = "__all__"
