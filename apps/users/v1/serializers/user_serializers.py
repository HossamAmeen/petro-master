from rest_framework import serializers

from apps.users.models import FirebaseToken, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "name", "email", "phone_number", "role"]


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
            "created_by",
            "updated_by",
        ]


class FirebaseTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirebaseToken
        fields = ["id", "token", "created"]


class FirebaseTokenDeleteSerializer(serializers.Serializer):
    token = serializers.CharField(help_text="Firebase token to be deleted")
