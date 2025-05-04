from rest_framework import serializers

from apps.companies.models.company_models import Driver
from apps.companies.v1.serializers.branch_serializers import (
    SingleBranchWithDistrictSerializer,
)


class ListDriverSerializer(serializers.ModelSerializer):
    branch = SingleBranchWithDistrictSerializer()

    class Meta:
        model = Driver
        exclude = ("created_by", "updated_by")


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        exclude = ("created_by", "updated_by")
        read_only_fields = ("code",)


class SingleDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ["id", "name", "phone_number", "branch", "code"]
