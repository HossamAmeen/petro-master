from rest_framework import serializers

from apps.companies.models.company_models import Car
from apps.companies.v1.serializers.branch_serializers import (
    SingleBranchWithDistrictSerializer,
)
from apps.utilities.serializers import BalanceUpdateSerializer


class ListCarSerializer(serializers.ModelSerializer):
    branch = SingleBranchWithDistrictSerializer()

    class Meta:
        model = Car
        fields = "__all__"


class CarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Car
        fields = "__all__"


class CarBalanceUpdateSerializer(BalanceUpdateSerializer):
    pass
