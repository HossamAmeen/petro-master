from django.contrib import admin

from apps.notifications.models import Notification
from apps.users.models import CompanyUser

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
        "created",
        "modified",
        "created_by",
        "updated_by",
    )
    list_filter = (
        "is_incoming",
        "status",
        "company",
        "company__branches",
    )

    def has_change_permission(self, request, obj=None):
        if obj and obj.status != CompanyKhaznaTransaction.TransactionStatus.PENDING:
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
            super().save_model(request, obj, form, change)

        company_branch = form.cleaned_data.get("company_branch")
        if company_branch:
            obj.company = company_branch.company
        if obj.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED:
            # send notifications
            if not obj.is_internal:
                obj.update_company_balance()
                company_owner = CompanyUser.objects.filter(
                    company=obj.company, role=CompanyUser.UserRoles.CompanyOwner
                ).first()
                message = f"تم شحن رصيد الشركة {obj.company.name} برصيد {obj.amount}"
                if company_owner:
                    Notification.objects.create(
                        user_id=company_owner.user.id,
                        title=message,
                        description=message,
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
        "created",
        "modified",
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
            if not obj.is_internal:
                obj.update_station_balance()
        obj.is_internal = False
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
