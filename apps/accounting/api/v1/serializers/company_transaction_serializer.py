from rest_framework import serializers

from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)
from apps.notifications.models import Notification
from apps.shared.base_exception_class import CustomValidationError
from apps.shared.generate_code import generate_unique_code
from apps.stations.api.v1.serializers import StationBranchWithDistrictSerializer
from apps.users.models import CompanyUser, StationOwner


class ListCompanyKhaznaTransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyKhaznaTransaction
        fields = "__all__"


class ListCompanyKhaznaTransactionForDashboardSerializer(serializers.ModelSerializer):
    company_branch_name = serializers.SerializerMethodField()

    class Meta:
        model = CompanyKhaznaTransaction
        fields = "__all__"

    def get_company_branch_name(self, obj):
        return obj.company_branch.name if obj.company_branch else None


class CreateCompanyKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyKhaznaTransaction
        exclude = ("created_by", "updated_by", "reference_code", "is_internal")

    def create(self, validated_data):
        validated_data["reference_code"] = generate_unique_code(
            model=CompanyKhaznaTransaction,
            look_up="reference_code",
            min_value=10**8,
            max_value=10**9,
        )
        instance = super().create(validated_data)

        if instance.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED:
            users_to_notify = list(
                CompanyUser.objects.filter(
                    company=instance.company,
                    role=CompanyUser.UserRoles.CompanyOwner,
                ).values_list("id", flat=True)
            )
            if instance.company_branch:
                instance.update_company_balance(instance.company_branch)
                users_to_notify = list(
                    CompanyUser.objects.filter(
                        company=instance.company,
                        role=CompanyUser.UserRoles.CompanyBranchManager,
                        company_branch_managers__company_branch=instance.company_branch,
                    ).values_list("id", flat=True)
                )
                message = f"تم شحن رصيد الفرع {instance.company_branch.name} برصيد {instance.amount}"
            else:
                instance.update_company_balance(instance.company)
                message = f"تم شحن رصيد الشركة {instance.company.name} برصيد {instance.amount}"
            # send notifications
            for user_id in users_to_notify:
                Notification.objects.create(
                    user_id=user_id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
        return instance


class UpdateCompanyKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyKhaznaTransaction
        exclude = ("created_by", "updated_by", "reference_code", "is_internal")

    def update(self, instance, validated_data):
        if instance.status in [
            KhaznaTransaction.TransactionStatus.APPROVED,
            KhaznaTransaction.TransactionStatus.DECLINED,
        ]:
            raise CustomValidationError("لا يمكن اتمام عملية هيا منهيه بالفعل")

        instance = super().update(instance, validated_data)
        instance.save()

        if instance.status == KhaznaTransaction.TransactionStatus.APPROVED:
            users_to_notify = list(
                CompanyUser.objects.filter(
                    company=instance.company,
                    role=CompanyUser.UserRoles.CompanyOwner,
                ).values_list("id", flat=True)
            )
            if instance.company_branch:
                instance.update_company_balance(instance.company_branch)
                users_to_notify = list(
                    CompanyUser.objects.filter(
                        company=instance.company,
                        role=CompanyUser.UserRoles.CompanyBranchManager,
                        company_branch_managers__company_branch=instance.company_branch,
                    ).values_list("id", flat=True)
                )
                message = f"تم شحن رصيد الفرع {instance.company_branch.name} برصيد {instance.amount}"
            else:
                instance.update_company_balance(instance.company)
                message = f"تم شحن رصيد الشركة {instance.company.name} برصيد {instance.amount}"
            # send notifications
            for user_id in users_to_notify:
                Notification.objects.create(
                    user_id=user_id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
        return instance


class StationKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationKhaznaTransaction
        fields = "__all__"


class KhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = KhaznaTransaction
        fields = "__all__"


class CreateStationKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationKhaznaTransaction
        exclude = ("created_by", "updated_by", "reference_code", "is_internal")

    def create(self, validated_data):
        validated_data["reference_code"] = generate_unique_code(
            model=StationKhaznaTransaction,
            look_up="reference_code",
            min_value=10**8,
            max_value=10**9,
        )
        instance = super().create(validated_data)

        if instance.status == KhaznaTransaction.TransactionStatus.APPROVED:
            users_to_notify = list(
                StationOwner.objects.filter(
                    station=instance.station,
                    role=StationOwner.UserRoles.StationOwner,
                ).values_list("id", flat=True)
            )
            if instance.station_branch:
                instance.update_station_balance(instance.station_branch)
                users_to_notify = list(
                    StationOwner.objects.filter(
                        station=instance.station,
                        role=StationOwner.UserRoles.StationBranchManager,
                        station_branch_managers__station_branch=instance.station_branch,
                    ).values_list("id", flat=True)
                )
                message = f"تم شحن رصيد الفرع {instance.station_branch.name} برصيد {instance.amount}"
            else:
                instance.update_station_balance(instance.station)
                message = f"تم شحن رصيد المحطة {instance.station.name} برصيد {instance.amount}"
            # send notifications
            for user_id in users_to_notify:
                Notification.objects.create(
                    user_id=user_id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
        return instance


class UpdateStationKhaznaTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationKhaznaTransaction
        exclude = ("created_by", "updated_by", "reference_code", "is_internal")

    def update(self, instance, validated_data):
        if instance.status in [
            KhaznaTransaction.TransactionStatus.APPROVED,
            KhaznaTransaction.TransactionStatus.DECLINED,
        ]:
            raise CustomValidationError("لا يمكن اتمام عملية هيا منهيه بالفعل")

        instance = super().update(instance, validated_data)

        instance.save()

        if instance.status == KhaznaTransaction.TransactionStatus.APPROVED:
            users_to_notify = list(
                StationOwner.objects.filter(
                    station=instance.station,
                    role=StationOwner.UserRoles.StationOwner,
                ).values_list("id", flat=True)
            )
            if instance.station_branch:
                instance.update_station_balance(instance.station_branch)
                users_to_notify = list(
                    StationOwner.objects.filter(
                        station=instance.station,
                        role=StationOwner.UserRoles.StationBranchManager,
                        station_branch_managers__station_branch=instance.station_branch,
                    ).values_list("id", flat=True)
                )
                message = f"تم شحن رصيد الفرع {instance.station_branch.name} برصيد {instance.amount}"
            else:
                instance.update_station_balance(instance.station)
                message = f"تم شحن رصيد المحطة {instance.station.name} برصيد {instance.amount}"
            # send notifications
            for user_id in users_to_notify:
                Notification.objects.create(
                    user_id=user_id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
        return instance


class ListStationKhaznaTransactionSerializer(serializers.ModelSerializer):
    station_branch = StationBranchWithDistrictSerializer(read_only=True)

    class Meta:
        model = StationKhaznaTransaction
        fields = "__all__"
