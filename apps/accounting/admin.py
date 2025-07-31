from django.contrib import admin
from django.core.exceptions import ValidationError

from apps.notifications.models import Notification
from apps.shared.generate_code import generate_unique_code
from apps.users.models import CompanyUser, StationOwner

from .models import CompanyKhaznaTransaction, StationKhaznaTransaction


@admin.register(CompanyKhaznaTransaction)
class CompanyKhaznaTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "amount",
        "is_incoming",
        "status",
        "reference_code",
        "description",
        "method",
        "company",
        "is_internal",
        "created",
        "modified",
    )
    search_fields = (
        "reference_code",
        "description",
        "company__name",
    )
    readonly_fields = (
        "id",
        "reference_code",
        "is_internal",
        "for_what",
        "reviewed_by",
        "created",
        "modified",
        "created_by",
        "updated_by",
    )
    list_filter = (
        "is_incoming",
        "status",
        "company",
        "company_branch",
    )

    def has_change_permission(self, request, obj=None):
        if obj and obj.status != CompanyKhaznaTransaction.TransactionStatus.PENDING:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "company_branch":
            kwargs["required"] = False
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
            obj.reference_code = generate_unique_code(
                model=CompanyKhaznaTransaction,
                look_up="reference_code",
                min_value=10**8,
                max_value=10**9,
            )
            super().save_model(request, obj, form, change)

        company_branch = form.cleaned_data.get("company_branch")
        company_branches = list(obj.company.branches.values_list("id", flat=True))
        if company_branch and company_branch.id not in company_branches:
            raise ValidationError("Invalid company branch")
        if obj.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED:
            users_to_notify = []
            if company_branch:
                obj.update_company_balance(company_branch)
                notification_message = (
                    f"تم شحن الفرع {company_branch.name} برصيد {obj.amount}"
                )
                users_to_notify = list(
                    CompanyUser.objects.filter(
                        company=company_branch.company,
                        role=CompanyUser.UserRoles.CompanyBranchManager,
                    ).values_list("id", flat=True)
                )
            else:
                obj.update_company_balance(obj.company)
                notification_message = (
                    f"تم شحن رصيد الشركة {obj.company.name} برصيد {obj.amount}"
                )
            # send notifications
            company_owner = list(
                CompanyUser.objects.filter(
                    company=obj.company, role=CompanyUser.UserRoles.CompanyOwner
                ).values_list("id", flat=True)
            )
            users_to_notify.extend(company_owner)
            for user_id in users_to_notify:
                Notification.objects.create(
                    user_id=user_id,
                    title=notification_message,
                    description=notification_message,
                    type=Notification.NotificationType.MONEY,
                )

        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StationKhaznaTransaction)
class StationKhaznaTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "amount",
        "is_incoming",
        "status",
        "reference_code",
        "description",
        "method",
        "station",
        "is_internal",
        "created",
        "modified",
    )
    search_fields = (
        "reference_code",
        "description",
        "station__name",
    )
    list_filter = (
        "is_incoming",
        "is_internal",
        "status",
        "station",
        "station__branches",
    )
    readonly_fields = (
        "id",
        "reference_code",
        "is_internal",
        "reviewed_by",
        "created",
        "modified",
        "created_by",
        "updated_by",
    )

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        fields = [field for field in fields if field not in ["is_internal"]]
        return fields

    def has_change_permission(self, request, obj=None):
        if obj and obj.status != StationKhaznaTransaction.TransactionStatus.PENDING:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):

        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
            super().save_model(request, obj, form, change)

        station_branch = form.cleaned_data.get("station_branch")
        if station_branch:
            obj.station = station_branch.station
        if obj.status == StationKhaznaTransaction.TransactionStatus.APPROVED:
            obj.update_station_balance()
            station_owner = StationOwner.objects.filter(
                station=obj.station, role=StationOwner.UserRoles.StationOwner
            ).first()
            message = f"تم شحن رصيد محطة {obj.station.name} برصيد {obj.amount}"
            if station_owner:
                Notification.objects.create(
                    user_id=station_owner.id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "station_branch":
            kwargs["required"] = False
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
