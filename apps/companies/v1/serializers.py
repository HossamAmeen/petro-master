from rest_framework import serializers

from apps.companies.models.company_models import Company, CompanyBranch, Driver
from apps.geo.v1.serializers import ListDistrictSerializer
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.stations.v1.serializers import ListStationSerializer
class ListCompanySerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()

    class Meta:
        model = Company
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'


class CompanyNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['name']


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


class ListCompanyBranchSerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()
    company = CompanyNameSerializer()
    cars_count = serializers.IntegerField()
    drivers_count = serializers.IntegerField()
    managers_count = serializers.IntegerField()

    class Meta:
        model = CompanyBranch
        fields = '__all__'


class CompanyBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBranch
        fields = '__all__'

class ListCompanyCashRequestSerializer(serializers.ModelSerializer):
    company = CompanySerializer()
    driver = ListDriverSerializer()
    station = ListStationSerializer()

    class Meta:
        model = CompanyCashRequest
        fields = '__all__'

class CompanyCashRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyCashRequest
        fields = '__all__'