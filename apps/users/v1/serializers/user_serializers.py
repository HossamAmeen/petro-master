from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.shared.base_exception_class import CustomValidationError
from apps.users.models import FirebaseToken, User


class CreateUserSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "phone_number",
            "role",
            "password",
            "confirm_password",
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
        validated_data.pop("confirm_password")
        return User.objects.create(**validated_data)

    def update(self, instance, validated_data):
        confirm_password = validated_data.pop("confirm_password")
        if validated_data.get("password"):
            if confirm_password != validated_data["password"]:
                raise CustomValidationError("Passwords do not match")
            validated_data["password"] = make_password(validated_data["password"])

        return super().update(instance, validated_data)


class SingleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "phone_number", "role"]


class ListUserSerializer(serializers.ModelSerializer):
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone_number",
            "role",
            "created",
            "modified",
            "is_active",
            "created_by",
            "updated_by",
        ]


class FirebaseTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirebaseToken
        fields = ["id", "token", "created"]


class FirebaseTokenDeleteSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="Firebase token to be deleted")
