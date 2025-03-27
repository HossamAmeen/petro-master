from rest_framework import serializers
from django.contrib.auth.hashers import make_password

from apps.users.models import CompanyUser

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyUser
        fields = ['id', 'name', 'email', 'phone_number', 'role', 'password']
        read_only_fields = ['id', 'phone_number', 'role']
        extra_kwargs = {'password': {'write_only': True}}

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)