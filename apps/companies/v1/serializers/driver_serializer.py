from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.companies.models.company_models import Driver
from apps.companies.v1.serializers.branch_serializers import (
    SingleBranchWithDistrictSerializer,
)


class ListDriverSerializer(serializers.ModelSerializer):
    branch = SingleBranchWithDistrictSerializer()
    is_license_expiring_soon = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        exclude = ("created_by", "updated_by")

    def get_is_license_expiring_soon(self, obj):
        if obj.lincense_expiration_date:
            today = timezone.now().date()
            expiry_date = obj.lincense_expiration_date
            time_difference = expiry_date - today
            return time_difference <= timedelta(days=30)
        return False


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        exclude = ("created_by", "updated_by")
        read_only_fields = ("code",)


class SingleDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ["id", "name", "phone_number", "branch", "code"]
