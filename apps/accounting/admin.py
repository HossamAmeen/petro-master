from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.notifications.models import Notification
from apps.shared.generate_code import generate_unique_code
from apps.users.models import CompanyUser, StationOwner


class CompanyKhaznaTransactionForm(forms.ModelForm):
    class Meta:
        model = CompanyKhaznaTransaction
        fields = "__all__"  # or specify your fields

    def clean(self):
        cleaned_data = super().clean()
        company_branch = cleaned_data.get("company_branch")

        if company_branch and "company" in cleaned_data:
            company = cleaned_data["company"]
            company_branches = list(company.branches.values_list("id", flat=True))

            if company_branch.id not in company_branches:
                raise ValidationError(
                    {"company_branch": "هذا الفرع لا ينمتي لهذه الشركة"}
                )

        return cleaned_data


@admin.register(CompanyKhaznaTransaction)
class CompanyKhaznaTransactionAdmin(admin.ModelAdmin):
    form = CompanyKhaznaTransactionForm
    list_per_page = 10
    list_max_show_all = 0  # Disable "Show all" link
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
        "is_internal",
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
        else:
            obj.updated_by = request.user
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

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("company")
        return qs


class StationKhaznaTransactionForm(forms.ModelForm):
    class Meta:
        model = StationKhaznaTransaction
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        station_branch = cleaned_data.get("station_branch")

        if station_branch and "station" in cleaned_data:
            station = cleaned_data["station"]
            station_branches = list(station.branches.values_list("id", flat=True))

            if station_branch.id not in station_branches:
                raise ValidationError(
                    {"station_branch": "هذا الفرع لا ينتمي لهذه المحطة"}
                )

        return cleaned_data


@admin.register(StationKhaznaTransaction)
class StationKhaznaTransactionAdmin(admin.ModelAdmin):
    form = StationKhaznaTransactionForm
    list_per_page = 10
    list_max_show_all = 0  # Disable "Show all" link
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
            obj.reference_code = generate_unique_code(
                model=StationKhaznaTransaction,
                look_up="reference_code",
                min_value=10**8,
                max_value=10**9,
            )
            super().save_model(request, obj, form, change)
        else:
            obj.updated_by = request.user
            super().save_model(request, obj, form, change)

        if obj.status == StationKhaznaTransaction.TransactionStatus.APPROVED:
            users_to_notify = []
            if obj.station_branch:
                obj.update_station_balance(obj.station_branch)
                users_to_notify = list(
                    StationOwner.objects.filter(
                        station=obj.station,
                        role=StationOwner.UserRoles.StationBranchManager,
                    ).values_list("id", flat=True)
                )
                message = (
                    f"تم شحن رصيد الفرع {obj.station_branch.name} برصيد {obj.amount}"
                )
            else:
                obj.update_station_balance(obj.station)
                users_to_notify = list(
                    StationOwner.objects.filter(
                        station=obj.station, role=StationOwner.UserRoles.StationOwner
                    ).values_list("id", flat=True)
                )
                message = f"تم شحن رصيد محطة {obj.station.name} برصيد {obj.amount}"
            for user_id in users_to_notify:
                Notification.objects.create(
                    user_id=user_id,
                    title=message,
                    description=message,
                    type=Notification.NotificationType.MONEY,
                )
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "station_branch":
            kwargs["required"] = False
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("station")
        return qs
