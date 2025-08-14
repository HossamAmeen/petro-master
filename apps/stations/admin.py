from django.contrib import admin
from django.db.models import Sum
from django.urls import reverse
from django.utils.html import format_html

from apps.users.models import StationBranchManager

from .models.service_models import Service
from .models.stations_models import Station, StationBranch, StationBranchService


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "unit",
        "cost",
        "created_by",
        "updated_by",
    )  # Display in list view
    list_filter = ("type", "unit")  # Filter sidebar
    search_fields = ("name",)  # Search by name
    readonly_fields = ("created_by", "updated_by")  # Hide created_by from the form

    def save_model(self, request, obj, form, change):
        """Assign the logged-in user to created_by before saving."""
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "address",
        "balance",
        "branches_link",
        "managers_link",
        "district",
        "created_by",
        "updated_by",
    )
    search_fields = ("name", "address", "district__name")
    readonly_fields = ("created_by", "updated_by")

    def branches_link(self, obj):
        count = obj.branches.count()
        url = (
            reverse("admin:stations_stationbranch_changelist")
            + f"?station__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Branches ({})</a>', url, count)

    branches_link.short_description = "Branches"

    def managers_link(self, obj):
        count = StationBranchManager.objects.filter(
            station_branch__station_id=obj.id
        ).count()
        url = (
            reverse("admin:users_stationowner_changelist")
            + f"?station_id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Managers ({})</a>', url, count)

    managers_link.short_description = "Managers"

    def save_model(self, request, obj, form, change):
        """Assign the logged-in user to created_by before saving."""
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# @admin.register(StationService)
# class StationServiceAdmin(admin.ModelAdmin):
#     list_display = (
#         "service",
#         "station",
#         "created_by",
#         "updated_by",
#     )
#     readonly_fields = ("created_by", "updated_by")
#     search_fields = ("service__name", "station__name")
#     list_filter = ("station", "service")

#     def save_model(self, request, obj, form, change):
#         """Assign the logged-in user to created_by before saving."""
#         if not obj.pk:  # Only set created_by on creation, not updates
#             obj.created_by = request.user
#         obj.updated_by = request.user
#         super().save_model(request, obj, form, change)


@admin.register(StationBranch)
class StationBranchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "address",
        "station",
        "balance",
        "district",
        "managers_link",
        "workers_link",
        "operations_link",
        "total_cost",
        "created_by",
        "updated_by",
    )
    readonly_fields = ("created_by", "updated_by")
    list_filter = ("station",)
    search_fields = ("name", "address")
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 20

    def managers_link(self, obj):
        count = obj.managers.count()
        url = (
            reverse("admin:users_stationbranchmanager_changelist")
            + f"?station_branch__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Managers ({})</a>', url, count)

    managers_link.short_description = "Managers"

    def workers_link(self, obj):
        count = obj.workers.count()
        url = (
            reverse("admin:users_worker_changelist")
            + f"?station_branch__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Workers ({})</a>', url, count)

    workers_link.short_description = "Workers"

    def operations_link(self, obj):
        count = obj.operations.count()
        url = (
            reverse("admin:companies_caroperation_changelist")
            + f"?station_branch__id__exact={obj.id}"
        )
        return format_html(
            '<a class="button" href="{}">Operations ({})</a>', url, count
        )

    operations_link.short_description = "Operations"

    def total_cost(self, obj):
        return obj.operations.aggregate(Sum("station_cost"))["station_cost__sum"] or 0

    total_cost.short_description = "Total Cost"

    def save_model(self, request, obj, form, change):
        """Assign the logged-in user to created_by before saving."""
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(StationBranchService)
class StationBranchServiceAdmin(admin.ModelAdmin):
    list_display = (
        "service",
        "station_branch",
        "created_by",
        "updated_by",
    )
    readonly_fields = ("created_by", "updated_by")
    search_fields = ("service__name", "station_branch__name")
    list_filter = ("station_branch", "service", "station_branch__station")

    def save_model(self, request, obj, form, change):
        """Assign the logged-in user to created_by before saving."""
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
