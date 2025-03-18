from rest_framework import serializers

from .models import CompanyBranch, Driver


class SingleBranchWithDistrictSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source='district.name')

    class Meta:
        model = CompanyBranch
        fields = ['id', 'name', 'email', 'phone_number', 'district']


class ListDriverSerializer(serializers.ModelSerializer):
    branch = SingleBranchWithDistrictSerializer()

    class Meta:
        model = Driver
        exclude = ('created_by', 'updated_by')


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        exclude = ('created_by', 'updated_by')
        read_only_fields = ('code',)
