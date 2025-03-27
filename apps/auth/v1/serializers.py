from rest_framework import serializers

from apps.users.models import CompanyUser

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyUser
        fields = ['id', 'name', 'email', 'phone_number', 'role']
        read_only_fields = ['id', 'phone_number', 'role']
