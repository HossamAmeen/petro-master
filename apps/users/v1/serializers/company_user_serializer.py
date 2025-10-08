from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.companies.models.company_models import CompanyBranch
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.constants import DASHBOARD_ROLES
from apps.users.models import CompanyBranchManager, CompanyUser, User

from .user_serializers import SingleUserSerializer


class CreateCompanyOwnerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=True, write_only=True)
    company_branches = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    company_id = serializers.IntegerField(required=False)

    class Meta:
        model = CompanyUser
        fields = [
            "id",
            "name",
            "email",
            "phone_number",
            "role",
            "password",
            "company_id",
            "company_branches",
        ]

    def validate(self, attrs):
        if self.context["request"].user.role in DASHBOARD_ROLES:
            if "company_id" not in attrs:
                raise CustomValidationError("لازم اختيار الشركة")

            if "company_branches" in attrs:
                self.company_branches = CompanyBranch.objects.filter(
                    id__in=attrs["company_branches"], company_id=attrs["company_id"]
                )
                if self.company_branches.count() != len(attrs["company_branches"]):
                    raise CustomValidationError("بعض الفروع غير موجودة في المحطة")
        return super().validate(attrs)

    def create(self, validated_data):
        validated_data["role"] = User.UserRoles.CompanyOwner
        validated_data["email"] = validated_data.get(
            "email", validated_data["phone_number"] + "@petro.com"
        )
        validated_data["password"] = make_password(validated_data["password"])
        company_branches = validated_data.pop("company_branches")
        company_user = CompanyUser.objects.create(**validated_data)
        if company_branches:
            CompanyBranchManager.objects.bulk_create(
                [
                    CompanyBranchManager(
                        user=company_user,
                        company_branch_id=branch,
                        created_by=self.context["request"].user,
                        updated_by=self.context["request"].user,
                    )
                    for branch in company_branches
                ]
            )
        return company_user

    def update(self, instance, validated_data):
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
        if "company_branches" in validated_data:
            instance.company_branch_managers.all().delete()
            CompanyBranchManager.objects.bulk_create(
                [
                    CompanyBranchManager(
                        user=instance,
                        company_branch_id=branch,
                        created_by=self.context["request"].user,
                        updated_by=self.context["request"].user,
                    )
                    for branch in validated_data["company_branches"]
                ]
            )
        return super().update(instance, validated_data)


class ListCompanyOwnerSerializer(serializers.ModelSerializer):
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()

    class Meta:
        model = CompanyUser
        fields = [
            "id",
            "name",
            "email",
            "phone_number",
            "role",
            "password",
            "created",
            "modified",
            "created_by",
            "updated_by",
            "company_id",
        ]


class ListCompanyBranchManagerSerializer(serializers.ModelSerializer):
    created_by = SingleUserSerializer()
    updated_by = SingleUserSerializer()

    class Meta:
        model = CompanyUser
        fields = [
            "id",
            "name",
            "email",
            "phone_number",
            "role",
            "password",
            "created",
            "modified",
            "created_by",
            "updated_by",
            "company_id",
        ]


class CompanyBranchManagerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=True, write_only=True)

    class Meta:
        model = CompanyUser
        fields = ["id", "name", "email", "phone_number", "role", "password"]

    def create(self, validated_data):
        validated_data["role"] = User.UserRoles.CompanyBranchManager
        validated_data["email"] = validated_data.get(
            "email", validated_data["phone_number"] + "@petro.com"
        )
        validated_data["password"] = make_password(validated_data["password"])
        validated_data["company_id"] = self.context["request"].company_id
        return CompanyUser.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data["company_id"] = self.context["request"].company_id
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])
        return super().update(instance, validated_data)
