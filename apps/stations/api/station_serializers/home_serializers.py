from rest_framework import serializers

from apps.companies.models.operation_model import CarOperation
from apps.stations.models.service_models import Service

SERVICE_UNIT_CHOICES = {
    Service.ServiceUnit.LITRE: "لتر",
    Service.ServiceUnit.UNIT: "وحدة",
    Service.ServiceUnit.OTHER: "غير ",
}


class ListStationReportsSerializer(serializers.ModelSerializer):
    service = serializers.IntegerField()
    service_name = serializers.CharField()
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    count = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.SerializerMethodField()

    class Meta:
        model = CarOperation
        fields = ["service", "service_name", "total_balance", "count", "amount", "unit"]

    def get_unit(self, obj):
        return SERVICE_UNIT_CHOICES.get(obj["unit"])
