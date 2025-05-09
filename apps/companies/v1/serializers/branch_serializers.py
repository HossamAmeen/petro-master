from rest_framework import serializers

from apps.companies.models.company_models import CompanyBranch
from apps.companies.v1.serializers.company_serializer import CompanyNameSerializer
from apps.geo.v1.serializers import ListDistrictSerializer
from apps.users.models import CompanyBranchManager, CompanyUser, User
from apps.users.v1.serializers.company_user_serializer import SingleUserSerializer
from apps.utilities.serializers import BalanceUpdateSerializer


class SingleBranchWithDistrictSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source="district.name")
    city = serializers.CharField(source="district.city.name")

    class Meta:
        model = CompanyBranch
        fields = ["id", "name", "email", "phone_number", "district", "city", "company"]


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


class BranchBalanceUpdateSerializer(BalanceUpdateSerializer):
    pass
