from rest_framework import serializers

from apps.users.models import User


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


class ListCompanyBranchManagerSerializer(serializers.ModelSerializer):
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone_number', 'role', 'created', 'modified', 'created_by', 'updated_by']
 
 
class CompanyBranchManagerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone_number', 'role']

    def create(self, validated_data):
        validated_data['role'] = User.UserRoles.CompanyBranchManager
        validated_data['email'] = validated_data.get('email', validated_data['phone_number'] + '@petro.com')
        return User.objects.create(**validated_data)
