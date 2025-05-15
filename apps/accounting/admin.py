from django.contrib import admin

from .models import CompanyKhaznaTransaction


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
