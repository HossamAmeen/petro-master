from rest_framework import serializers

from apps.geo.serializers import ListDistrictSerializer

from .models import Company, CompanyBranch, Driver


class ListCompanySerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()

    class Meta:
        model = Company
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


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


class ListCompanyBranchSerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()
    company = ListCompanySerializer()

    class Meta:
        model = CompanyBranch
        fields = '__all__'


class CompanyBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBranch
        fields = '__all__'
