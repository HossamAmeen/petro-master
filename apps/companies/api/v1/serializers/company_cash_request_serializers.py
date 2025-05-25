from rest_framework import serializers

from apps.companies.api.v1.serializers.driver_serializer import SingleDriverSerializer
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Company, Driver
from apps.stations.v1.serializers import ListStationSerializer
from apps.users.models import User


class ListCompanyCashRequestSerializer(serializers.ModelSerializer):
    driver = SingleDriverSerializer()
    station = ListStationSerializer()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = CompanyCashRequest
        fields = [
            "id",
            "driver",
            "amount",
            "status",
            "company",
            "station",
            "created",
            "modified",
            "is_owner",
        ]

    def get_is_owner(self, obj):
        request = self.context["request"]
        if request.user.role == User.UserRoles.CompanyOwner:
            return True
        if request.user.role == User.UserRoles.CompanyBranchManager:
            return obj.created_by == request.user
        return False


class CompanyCashRequestSerializer(serializers.ModelSerializer):
    driver = serializers.PrimaryKeyRelatedField(
        queryset=Driver.objects.none(),
        error_messages={
            "does_not_exist": "هذا السائق غير موجود",
            "incorrect_type": "Invalid type. Expected a driver ID.",
        },
    )

    class Meta:
        model = CompanyCashRequest
        fields = ["driver", "amount"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        queryset = Driver.objects.all()
        if request.user.role == User.UserRoles.CompanyOwner:
            queryset = queryset.filter(branch__company_id=request.company_id)
        if request.user.role == User.UserRoles.CompanyBranchManager:
            queryset = queryset.filter(branch__managers__user=request.user)

        self.fields["driver"].queryset = queryset

    def validate(self, attrs):
        request = self.context["request"]
        if request.user.role == User.UserRoles.CompanyOwner:
            parent_balance = (
                Company.objects.filter(id=request.company_id).first().balance
            )
        else:
            driver = Driver.objects.filter(id=request.data["driver"]).first()
            parent_balance = driver.branch.balance
        if attrs["amount"] > parent_balance:
            raise serializers.ValidationError({"amount": "الرصيد غير كافي"})
        return attrs
