from rest_framework import serializers
from .models import Driver, CompanyBranch


class SingleBranchWithDistrictSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source='district.name')

    class Meta:
        model = CompanyBranch
        fields = ['id', 'name', 'email', 'phone_number', 'district']


class ListDriverSerializer(serializers.ModelSerializer):
    branch = SingleBranchWithDistrictSerializer()

    class Meta:
        model = Driver
        fields = '__all__'


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'
        read_only_fields = ('code',)
