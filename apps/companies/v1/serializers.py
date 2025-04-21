from rest_framework import serializers

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Company, CompanyBranch, Driver
from apps.geo.v1.serializers import ListDistrictSerializer
from apps.stations.v1.serializers import ListStationSerializer
from apps.users.models import CompanyBranchManager, CompanyUser, User
from apps.users.v1.serializers.company_user_serializer import SingleUserSerializer


class ListCompanySerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()

    class Meta:
        model = Company
        fields = "__all__"


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = "__all__"


class CompanyNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["name"]


class SingleBranchWithDistrictSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source="district.name")

    class Meta:
        model = CompanyBranch
        fields = ["id", "name", "email", "phone_number", "district", "company"]


class ListDriverSerializer(serializers.ModelSerializer):
    branch = SingleBranchWithDistrictSerializer()

    class Meta:
        model = Driver
        exclude = ("created_by", "updated_by")


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        exclude = ("created_by", "updated_by")
        read_only_fields = ("code",)


class SingleDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ["id", "name", "phone_number", "branch", "code"]


class ListCompanyBranchSerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()
    company = CompanyNameSerializer()
    cars_count = serializers.IntegerField()
    drivers_count = serializers.IntegerField()
    managers_count = serializers.IntegerField()

    class Meta:
        model = CompanyBranch
        fields = "__all__"


class RetrieveCompanyBranchSerializer(serializers.ModelSerializer):
    district = ListDistrictSerializer()
    company = CompanyNameSerializer()
    cars_count = serializers.IntegerField()
    drivers_count = serializers.IntegerField()
    managers_count = serializers.IntegerField()
    managers = serializers.SerializerMethodField()

    class Meta:
        model = CompanyBranch
        fields = "__all__"

    def get_managers(self, obj):
        user_ids = (
            CompanyBranchManager.objects.filter(company_branch_id=obj.id)
            .values_list("user_id", flat=True)
            .distinct()
        )
        user_queryset = User.objects.filter(id__in=user_ids)
        return SingleUserSerializer(user_queryset, many=True).data


class CompanyBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBranch
        fields = "__all__"


class CompanyBranchUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBranch
        fields = ["name", "email", "phone_number", "address", "district"]


class CompanyBranchAssignManagersSerializer(serializers.Serializer):
    managers = serializers.ListField(child=serializers.IntegerField())

    def validate(self, attrs):
        if not attrs["managers"]:
            raise serializers.ValidationError(
                {"message": "يجب إرسال قائمة بمعرفات المديرين"}
            )

        manager_ids = attrs["managers"]

        # Get valid users from the same company
        valid_managers = CompanyUser.objects.filter(
            id__in=manager_ids,
            company_id=self.context["request"].company_id,
            role=User.UserRoles.CompanyBranchManager,
        ).values_list("id", flat=True)

        invalid_ids = set(manager_ids) - set(valid_managers)
        if invalid_ids:
            raise serializers.ValidationError(
                {
                    "message": f"بعض المديرين لا ينتمون لشركتك (المعرفات غير الصالحة: {invalid_ids})",  # noqa
                    "errors": {"invalid_manager_ids": list(invalid_ids)},
                }
            )

        return attrs


class BranchBalanceUpdateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    type = serializers.ChoiceField(
        choices=[("add", "add"), ("subtract", "subtract")], required=True
    )


class ListCompanyCashRequestSerializer(serializers.ModelSerializer):
    driver = SingleDriverSerializer()
    station = ListStationSerializer()

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
        ]


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
        if request and hasattr(request, "company_id"):
            queryset = queryset.filter(branch__company_id=request.company_id)

        self.fields["driver"].queryset = queryset
