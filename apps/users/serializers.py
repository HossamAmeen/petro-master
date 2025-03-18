from rest_framework import serializers
from .models import User


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone_number', 'role']


class SingleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'phone_number', 'role']


class ListUserSerializer(serializers.ModelSerializer):
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone_number', 'role', 'created', 'modified', 'created_by', 'updated_by']
