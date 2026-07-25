from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from apps.companies.models.ai_api_response_model import AIApiResponse
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
    change_list_template = "admin/stations/stationbranch/change_list.html"
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
    list_per_page = 10

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "match-score-report/",
                self.admin_site.admin_view(self.match_score_report_view),
                name="stations_stationbranch_match_score_report",
            ),
        ]
        return custom_urls + urls

    def match_score_report_view(self, request):
        stats = (
            AIApiResponse.objects.values(
                "car_operation__station_branch_id",
                "car_operation__station_branch__name",
                "car_operation__station_branch__station__name",
            )
            .annotate(
                total_responses=Count("id"),
                match_100_count=Count("id", filter=Q(match_score=100)),
            )
            .order_by(
                "car_operation__station_branch__station__name",
                "car_operation__station_branch__name",
            )
        )

        rows = []
        for item in stats:
            total = item["total_responses"] or 0
            match_100 = item["match_100_count"] or 0
            percentage = (match_100 / total) * 100 if total else 0
            rows.append(
                {
                    "station_name": item[
                        "car_operation__station_branch__station__name"
                    ],
                    "branch_name": item["car_operation__station_branch__name"],
                    "match_100_count": match_100,
                    "total_responses": total,
                    "match_percentage": round(percentage, 2),
                }
            )

        rows.sort(
            key=lambda row: (row["match_percentage"], row["match_100_count"]),
            reverse=True,
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "AI Match Score Report",
            "rows": rows,
            "total_branches": len(rows),
            "opts": self.model._meta,
        }
        return TemplateResponse(
            request,
            "admin/stations/stationbranch/match_score_report.html",
            context,
        )

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
