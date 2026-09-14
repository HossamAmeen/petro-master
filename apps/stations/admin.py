from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.db.models import (
    Count,
    DecimalField,
    F,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from apps.companies.models.ai_api_response_model import AIApiResponse
from apps.companies.models.operation_model import CarOperation
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
    change_list_template = "admin/stations/station/change_list.html"
    list_display = (
        "name",
        "address",
        "balance",
        "total_balance",
        "branches_link",
        "managers_link",
        "operations_link",
        "district",
        "created_by",
        "updated_by",
    )
    search_fields = ("name", "address", "district__name")
    readonly_fields = ("balance", "created_by", "updated_by")

    def get_queryset(self, request):
        """Annotate the station balance parts and its operation count."""
        zero = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        branches_balance = Subquery(
            StationBranch.objects.filter(station_id=OuterRef("pk"))
            .values("station_id")
            .annotate(total=Sum("balance"))
            .values("total")[:1]
        )
        operations_count = Subquery(
            CarOperation.objects.filter(station_branch__station_id=OuterRef("pk"))
            .values("station_branch__station_id")
            .annotate(total=Count("id"))
            .values("total")[:1]
        )
        return (
            super()
            .get_queryset(request)
            .annotate(
                total_balance_sum=F("balance") + Coalesce(branches_balance, zero),
                operations_count=Coalesce(operations_count, Value(0)),
            )
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        try:
            # totals must reflect the active search/list_filter selection
            queryset = self.get_changelist_instance(request).get_queryset(request)
        except IncorrectLookupParameters:
            # let ModelAdmin.changelist_view handle it (redirects to ?e=1)
            queryset = self.model._default_manager.none()

        station_ids = queryset.values("pk")
        stations_balance = (
            Station.objects.filter(pk__in=station_ids).aggregate(total=Sum("balance"))[
                "total"
            ]
            or 0
        )
        branches_balance = (
            StationBranch.objects.filter(station__in=station_ids).aggregate(
                total=Sum("balance")
            )["total"]
            or 0
        )

        extra_context["sum_total_balance"] = stations_balance + branches_balance
        extra_context["sum_operations_count"] = CarOperation.objects.filter(
            station_branch__station__in=station_ids
        ).count()
        return super().changelist_view(request, extra_context=extra_context)

    def total_balance(self, obj):
        return obj.total_balance_sum

    total_balance.short_description = "Total Balance"
    total_balance.admin_order_field = "total_balance_sum"

    def operations_link(self, obj):
        url = (
            reverse("admin:companies_caroperation_changelist")
            + f"?station_branch__station__id__exact={obj.id}"
        )
        return format_html(
            '<a class="button" href="{}">Operations ({})</a>',
            url,
            obj.operations_count,
        )

    operations_link.short_description = "Operations"
    operations_link.admin_order_field = "operations_count"

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
    readonly_fields = ("balance", "created_by", "updated_by")
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

        fuel_image_ops_by_branch = dict(
            CarOperation.objects.filter(fuel_image__isnull=False)
            .exclude(fuel_image="")
            .values("station_branch_id")
            .annotate(total=Count("id"))
            .values_list("station_branch_id", "total")
        )

        rows = []
        for item in stats:
            total = item["total_responses"] or 0
            match_100 = item["match_100_count"] or 0
            percentage = (match_100 / total) * 100 if total else 0
            branch_id = item["car_operation__station_branch_id"]
            ai_responses_url = None
            if branch_id:
                ai_responses_url = (
                    reverse("admin:companies_aiapiresponse_changelist")
                    + f"?car_operation__station_branch__id__exact={branch_id}"
                    + "&page_size=100"
                )
            rows.append(
                {
                    "station_name": item[
                        "car_operation__station_branch__station__name"
                    ],
                    "branch_name": item["car_operation__station_branch__name"],
                    "ai_responses_url": ai_responses_url,
                    "fuel_image_ops_count": fuel_image_ops_by_branch.get(branch_id, 0),
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
