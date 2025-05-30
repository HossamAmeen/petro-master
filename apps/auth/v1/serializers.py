from django.contrib.auth.hashers import make_password
from django.db.models import Sum
from rest_framework import serializers

from apps.companies.models.company_models import CompanyBranch
from apps.users.models import User


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()


class ProfileSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email", "phone_number", "role", "password", "balance"]
        read_only_fields = ["id", "phone_number", "role", "balance"]
        extra_kwargs = {"password": {"write_only": True}}

    def update(self, instance, validated_data):
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
        return super().update(instance, validated_data)

    def get_balance(self, obj):
        if obj.role == User.UserRoles.CompanyOwner:
            return obj.companyuser.company.balance
        elif obj.role == User.UserRoles.CompanyBranchManager:
            return (
                CompanyBranch.objects.filter(managers__user=obj).aggregate(
                    Sum("balance")
                )["balance__sum"]
                or 0
            )
        elif obj.role == User.UserRoles.StationOwner:
            return obj.stationowner.station.balance
        elif obj.role == User.UserRoles.StationBranchManager:
            return (
                obj.stationowner.station.branches.filter(managers__user=obj).aggregate(
                    Sum("balance")
                )["balance__sum"]
                or 0
            )
        elif obj.role == User.UserRoles.StationWorker:
            return 0
        return 0


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"password": "Passwords must match."})
        return data
