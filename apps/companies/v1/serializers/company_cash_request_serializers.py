from rest_framework import serializers

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Driver
from apps.companies.v1.serializers.driver_serializer import SingleDriverSerializer
from apps.stations.v1.serializers import ListStationSerializer


class ListCompanyCashRequestSerializer(serializers.ModelSerializer):
    driver = SingleDriverSerializer()
    station = ListStationSerializer()

    class Meta:
        model = CompanyCashRequest
        fields = [
            "id",
            "driver",
            "amount",
            "status",
            "company",
            "station",
            "created",
            "modified",
        ]


class CompanyCashRequestSerializer(serializers.ModelSerializer):
    driver = serializers.PrimaryKeyRelatedField(
        queryset=Driver.objects.none(),
        error_messages={
            "does_not_exist": "هذا السائق غير موجود",
            "incorrect_type": "Invalid type. Expected a driver ID.",
        },
    )

    class Meta:
        model = CompanyCashRequest
        fields = ["driver", "amount"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        queryset = Driver.objects.all()
        if request and hasattr(request, "company_id"):
            queryset = queryset.filter(branch__company_id=request.company_id)

        self.fields["driver"].queryset = queryset
