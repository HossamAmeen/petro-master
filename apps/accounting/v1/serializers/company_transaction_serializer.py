from rest_framework import serializers

from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)


class CompanyKhaznaTransactionSerializer(serializers.ModelSerializer):
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
