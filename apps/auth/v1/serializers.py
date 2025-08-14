import logging

from django.contrib.auth.hashers import make_password
from django.db.models import Sum
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.state import token_backend

from apps.companies.models.company_models import CompanyBranch
from apps.shared.constants import COMPANY_ROLES, STATION_ROLES
from apps.users.models import User

logger = logging.getLogger(__name__)


class CompanyTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        # Get standard token response
        data = super().validate(attrs)

        try:
            # Decode without using OutstandingToken
            payload = token_backend.decode(attrs["refresh"], verify=True)
            access_payload = token_backend.decode(data["access"], verify=False)
            payload.get("company_id")

            if payload.get("role") in STATION_ROLES:
                if not payload.get("station_id"):
                    raise serializers.ValidationError("Station ID required")
                access_payload["station_id"] = payload.get("station_id")
            elif payload.get("role") in COMPANY_ROLES:
                if not payload.get("company_id"):
                    raise serializers.ValidationError("Company ID required")
                access_payload["company_id"] = payload.get("company_id")

            data["access"] = token_backend.encode(access_payload)

            return data

        except Exception as e:
            raise serializers.ValidationError(str(e))


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone_number",
            "role",
            "password",
        ]
        read_only_fields = ["id", "phone_number", "role"]
        extra_kwargs = {"password": {"write_only": True}}

    def update(self, instance, validated_data):
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.role == User.UserRoles.CompanyOwner:
            data["balance"] = instance.companyuser.company.balance
        elif instance.role == User.UserRoles.CompanyBranchManager:
            data["balance"] = (
                CompanyBranch.objects.filter(managers__user=instance).aggregate(
                    Sum("balance")
                )["balance__sum"]
                or 0
            )
        elif instance.role == User.UserRoles.StationOwner:
            data["balance"] = instance.stationowner.station.balance
        elif instance.role == User.UserRoles.StationBranchManager:
            data["balance"] = (
                instance.stationowner.station.branches.filter(
                    managers__user=instance
                ).aggregate(Sum("balance"))["balance__sum"]
                or 0
            )
        elif instance.role == User.UserRoles.StationWorker:
            data["balance"] = 0
        data["available_balance"] = self.get_available_balance(instance)
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords must match."})
        return data
