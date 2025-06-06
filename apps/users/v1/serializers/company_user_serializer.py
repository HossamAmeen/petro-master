from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.users.models import CompanyUser, User

from .user_serializers import SingleUserSerializer


class ListCompanyBranchManagerSerializer(serializers.ModelSerializer):
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()

    class Meta:
        model = CompanyUser
        fields = [
            "id",
            "name",
            "email",
            "phone_number",
            "role",
            "password",
            "created",
            "modified",
            "created_by",
            "updated_by",
            "company_id",
        ]


class CompanyBranchManagerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = CompanyUser
        fields = ["id", "name", "email", "phone_number", "role", "password"]

    def create(self, validated_data):
        validated_data["role"] = User.UserRoles.CompanyBranchManager
        validated_data["email"] = validated_data.get(
            "email", validated_data["phone_number"] + "@petro.com"
        )
        validated_data["password"] = make_password(validated_data["password"])
        validated_data["company_id"] = self.context["request"].company_id
        return CompanyUser.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["company_id"] = self.context["request"].company_id
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
        return super().update(instance, validated_data)
