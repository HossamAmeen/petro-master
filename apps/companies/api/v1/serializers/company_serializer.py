from rest_framework import serializers

from apps.companies.models.company_models import Company
from apps.geo.v1.serializers import ListDistrictSerializer
from apps.users.v1.serializers.user_serializers import SingleUserSerializer


class ListCompanySerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()
    total_branches = serializers.IntegerField()
    total_cars = serializers.IntegerField()
    total_drivers = serializers.IntegerField()
    total_managers = serializers.IntegerField()
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()

    class Meta:
        model = Company
        fields = "__all__"


class ListCompanyNameSerializer(serializers.ModelSerializer):

    class Meta:
        model = Company
        fields = ["id", "name"]


class CompanyCreationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["name", "email", "phone_number", "address", "district", "is_active"]


class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["name", "email", "phone_number", "address", "district", "is_active"]


class CompanyNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name"]
