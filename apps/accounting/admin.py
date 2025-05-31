from django.contrib import admin

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
    )


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
        "status",
        "station",
        "station__branches",
        "station__branches__managers__user",
    )
    readonly_fields = (
        "id",
        "created",
        "modified",
    )
