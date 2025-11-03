from django.contrib.auth.models import make_password
from django.db import transaction
from rest_framework import serializers

from apps.geo.v1.serializers import DistrictSerializer
from apps.shared.base_exception_class import CustomValidationError
from apps.users.models import Supervisor
from apps.users.v1.serializers.user_serializers import SingleUserSerializer


class ListSupervisorSerializer(serializers.ModelSerializer):
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()
    district = DistrictSerializer(many=True)

    class Meta:
        model = Supervisor
        fields = [
            "id",
            "name",
            "phone_number",
            "email",
            "district",
            "credit_limit",
            "role",
            "created_by",
            "updated_by",
        ]


class CreateSupervisorSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = Supervisor
        fields = [
            "name",
            "email",
            "phone_number",
            "role",
            "password",
            "confirm_password",
            "district",
            "credit_limit",
        ]

    def validate(self, attrs):
        if (
            self.context["request"].method == "POST"
            and attrs["password"] != attrs["confirm_password"]
        ):
            raise CustomValidationError("Passwords do not match")
        if self.context["request"].method == "PATCH" and attrs.get(
            "password"
        ) != attrs.get("confirm_password"):
            raise CustomValidationError("Passwords do not match")
        return attrs

    def create(self, validated_data):
        validated_data["email"] = validated_data.get(
            "email", validated_data["phone_number"] + "@petro.com"
        )
        validated_data["password"] = make_password(validated_data["password"])
        validated_data.pop("confirm_password", None)
        districts = validated_data.pop("district", None)
        with transaction.atomic():
            supervisor = Supervisor.objects.create(**validated_data)
            district_list = []
            for district in districts:
                district_list.append(district.id)
            supervisor.district.set(district_list)
        return supervisor

    def update(self, instance, validated_data):
        confirm_password = validated_data.pop("confirm_password", None)
        if validated_data.get("password"):
            if confirm_password != validated_data["password"]:
                raise CustomValidationError("Passwords do not match")
            validated_data["password"] = make_password(validated_data["password"])

        return super().update(instance, validated_data)
