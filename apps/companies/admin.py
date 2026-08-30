from datetime import datetime, time, timedelta

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.options import IncorrectLookupParameters
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, DecimalField, F, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.companies.models.operation_model import CarOperation, MonthlyInventory
from apps.companies.models.ai_api_response_model import AIApiResponse
from apps.geo.models import District
from apps.shared.generate_code import generate_unique_code
from apps.stations.models.service_models import Service

from .models.company_cash_models import CompanyCashRequest
from .models.company_models import Car, CarCode, Company, CompanyBranch, Driver
from django.core.exceptions import PermissionDenied


class CompanyBranchForm(forms.ModelForm):
    district = forms.ModelChoiceField(
        queryset=District.objects.all(),
        required=True,
        empty_label=None
    )

    class Meta:
        model = CompanyBranch
        fields = "__all__"


class BranchInline(admin.TabularInline):
    model = CompanyBranch
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    change_list_template = "admin/companies/company/change_list.html"
    list_display = (
        "name",
        "address",
        "phone_number",
        "total_balance",
        "branches_link",
        "cars_link",
        "drivers_link",
        "operations_link",
        "district",
        "created_by",
        "updated_by",
    )
    search_fields = ("name", "address", "phone_number")
    list_filter = ("district", "is_active")
    readonly_fields = ["balance", "created_by", "updated_by"]
    list_per_page = 10

    def get_queryset(self, request):
        """Annotate the company balance parts and its operation count."""
        zero = Value(0, output_field=DecimalField(max_digits=12, decimal_places=2))
        branches_balance = Subquery(
            CompanyBranch.objects.filter(company_id=OuterRef("pk"))
            .values("company_id")
            .annotate(total=Sum("balance"))
            .values("total")[:1]
        )
        cars_balance = Subquery(
            Car.objects.filter(branch__company_id=OuterRef("pk"))
            .values("branch__company_id")
            .annotate(total=Sum("balance"))
            .values("total")[:1]
        )
        operations_count = Subquery(
            CarOperation.objects.filter(car__branch__company_id=OuterRef("pk"))
            .values("car__branch__company_id")
            .annotate(total=Count("id"))
            .values("total")[:1]
        )
        return (
            super()
            .get_queryset(request)
            .annotate(
                total_balance_sum=(
                    F("balance")
                    + Coalesce(branches_balance, zero)
                    + Coalesce(cars_balance, zero)
                ),
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

        company_ids = queryset.values("pk")
        companies_balance = (
            Company.objects.filter(pk__in=company_ids).aggregate(total=Sum("balance"))[
                "total"
            ]
            or 0
        )
        branches_balance = (
            CompanyBranch.objects.filter(company__in=company_ids).aggregate(
                total=Sum("balance")
            )["total"]
            or 0
        )
        cars_balance = (
            Car.objects.filter(branch__company__in=company_ids).aggregate(
                total=Sum("balance")
            )["total"]
            or 0
        )

        extra_context["sum_total_balance"] = (
            companies_balance + branches_balance + cars_balance
        )
        extra_context["sum_operations_count"] = CarOperation.objects.filter(
            car__branch__company__in=company_ids
        ).count()
        return super().changelist_view(request, extra_context=extra_context)

    def total_balance(self, obj):
        return obj.total_balance_sum

    total_balance.short_description = "Total Balance"
    total_balance.admin_order_field = "total_balance_sum"

    def operations_link(self, obj):
        url = (
            reverse("admin:companies_caroperation_changelist")
            + f"?car__branch__company__id__exact={obj.id}"
        )
        return format_html(
            '<a class="button" href="{}">Operations ({})</a>',
            url,
            obj.operations_count,
        )

    operations_link.short_description = "Operations"
    operations_link.admin_order_field = "operations_count"

    def cars_link(self, obj):
        count = obj.branches.aggregate(total_cars=Count("cars"))["total_cars"] or 0
        url = (
            reverse("admin:companies_car_changelist")
            + f"?branch__company__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Cars ({})</a>', url, count)

    def drivers_link(self, obj):
        count = (
            obj.branches.aggregate(total_drivers=Count("drivers"))["total_drivers"] or 0
        )
        url = (
            reverse("admin:companies_driver_changelist")
            + f"?branch__company__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Drivers ({})</a>', url, count)

    def branches_link(self, obj):
        count = obj.branches.count()
        url = (
            reverse("admin:companies_companybranch_changelist")
            + f"?company__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Branches ({})</a>', url, count)

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new Driver.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
            obj.balance = 0
        obj.updated_by = request.user
        obj.save()

    drivers_link.short_description = "Drivers"
    cars_link.short_description = "Cars"
    branches_link.short_description = "Branches"


@admin.register(CompanyBranch)
class CompanyBranchAdmin(admin.ModelAdmin):
    form = CompanyBranchForm
    list_display = (
        "name",
        "email",
        "phone_number",
        "balance",
        "company",
        "car_link",
        "driver_link",
        "district",
        "created_by",
        "updated_by",
    )
    search_fields = ("name", "email", "phone_number")
    list_filter = ("company",)
    readonly_fields = ["balance", "created_by", "updated_by"]
    list_per_page = 20

    def car_link(self, obj):
        count = obj.cars.count()
        url = reverse("admin:companies_car_changelist") + f"?branch__id__exact={obj.id}"
        return format_html('<a class="button" href="{}">Cars ({})</a>', url, count)

    car_link.short_description = "Cars"

    def driver_link(self, obj):
        count = obj.drivers.count()
        url = (
            reverse("admin:companies_driver_changelist")
            + f"?branch__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Drivers ({})</a>', url, count)

    driver_link.short_description = "Drivers"

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new Driver.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
            obj.balance = 0
        if not obj.district:
            raise forms.ValidationError("District is required")
        obj.updated_by = request.user
        obj.save()


class CarForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(
            type__in=[Service.ServiceType.PETROL, Service.ServiceType.DIESEL]
        ),
        required=False,
    )
    fuel_allowed_days = forms.MultipleChoiceField(
        choices=Car.FuelAllowedDay.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    plate_color = forms.ChoiceField(
        choices=Car.PlateColor.choices, widget=forms.RadioSelect, required=True
    )

    class Meta:
        model = Car
        fields = "__all__"
        widgets = {
            "fuel_allowed_days": forms.CheckboxSelectMultiple(
                choices=Car.FuelAllowedDay.choices
            ),
            "plate_color": forms.RadioSelect(choices=Car.PlateColor.choices),
        }

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if not code:
            raise forms.ValidationError(_("This field is required."))

        car_code = CarCode.objects.filter(code=code).first()
        if not car_code:
            raise forms.ValidationError(_("كود العربيه لا يوجد في النظام"))

        if car_code.car and car_code.car != self.instance:
            raise forms.ValidationError(_("Car code is already assigned to another car."))

        return code

    def clean_fuel_allowed_days(self):
        fuel_allowed_days = self.cleaned_data.get("fuel_allowed_days")
        if not fuel_allowed_days:
            return []

        valid_choices = dict(Car.FuelAllowedDay.choices)
        for day in fuel_allowed_days:
            if day not in valid_choices:
                raise forms.ValidationError(f"{day} is not a valid choice.")
        return fuel_allowed_days


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    form = CarForm
    list_display = (
        "code",
        "plate_number",
        "plate_character",
        "plate_color",
        "color",
        "license_expiration_date",
        "brand",
        "permitted_fuel_amount",
        "fuel_type",
        "balance",
        "branch",
        "company_name",
        "operations_link",
    )
    search_fields = (
        "code",
        "plate_number",
        "plate_character",
        "brand",
    )
    list_filter = (
        "code",
        "color",
        "license_expiration_date",
        "model_year",
        "brand",
        "is_with_odometer",
        "tank_capacity",
        "fuel_type",
        "city",
        "branch",
        "branch__company",
    )
    readonly_fields = (
        "balance",
        "created_by",
        "updated_by",
        "created",
        "modified",
    )
    list_per_page = 10

    def company_name(self, obj):
        return obj.branch.company.name

    company_name.short_description = "Company"

    def operations_link(self, obj):
        url = reverse("admin:companies_caroperation_changelist") + f"?car__id__exact={obj.id}"
        return format_html('<a class="button" href="{}">Operations</a>', url)

    operations_link.short_description = "Operations"

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new Car.
        """
        if not obj.pk:  # Only set defaults on creation, not updates
            obj.created_by = request.user
            obj.balance = 0
            obj.fuel_consumption_rate = 0
            obj.number_of_fuelings_per_day = 0
            obj.number_of_washes_per_month = 0
            obj.fuel_allowed_days = form.cleaned_data.get("fuel_allowed_days", [])
            obj.is_blocked_balance_update = False

        obj.updated_by = request.user
        obj.save()

        # Handle CarCode linkage
        if obj.code:
            car_code = CarCode.objects.filter(code=obj.code).first()
            if car_code and car_code.car != obj:
                car_code.car = obj
                car_code.save()

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        fields_not_in_creation_form = [
            "last_meter",
            "fuel_consumption_rate",
            "number_of_fuelings_per_day",
            "number_of_washes_per_month",
            "fuel_allowed_days",
            "fuel_type",
        ]
        if not obj:
            fields = [
                field for field in fields if field not in fields_not_in_creation_form
            ]
        return fields


class CarCodeForm(forms.ModelForm):
    generate_count = forms.IntegerField(
        label="Number of codes to generate",
        min_value=1,
        max_value=10000,
        required=False,
        help_text="Leave empty to create just one code",
    )

    class Meta:
        model = CarCode
        fields = ["generate_count"]


@admin.register(CarCode)
class CarCodeAdmin(admin.ModelAdmin):
    form = CarCodeForm
    list_display = (
        "code",
        "car",
        "car_company_name",
        "created",
    )
    search_fields = (
        "code",
        "car__plate_number",
        "car__branch__company__name",
    )
    list_filter = ("car__branch__company", "created")
    actions = ["print_qr_codes"]
    list_select_related = ("car__branch__company",)
    list_per_page = 10
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 1000

    def save_model(self, request, obj, form, change):
        generate_count = form.cleaned_data.get("generate_count", 1)
        if generate_count > 1:
            # Generate multiple codes
            with transaction.atomic():
                code_list = []
                for i in range(generate_count):
                    code_list.append(generate_unique_code(CarCode))
                code_list = list(set(code_list))
                if len(code_list) < generate_count:
                    for i in range(generate_count - len(code_list)):
                        code_list.append(generate_unique_code(CarCode))
                code_list = list(set(code_list))
                CarCode.objects.bulk_create(
                    [
                        CarCode(
                            code=code,
                            car=obj.car,
                            created_by=request.user,
                            updated_by=request.user,
                        )
                        for code in code_list
                    ]
                )
            messages.success(
                request, f"Successfully generated {len(code_list)} car codes."
            )
            return
        else:
            if not obj.code:
                obj.code = generate_unique_code(CarCode)

        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

    def get_list_display_links(self, request, list_display):
        # Make only the car field clickable (or return None for no links)
        return []

    def print_qr_codes(self, request, queryset):
        from django.http import HttpResponse
        from django.template.loader import render_to_string

        html = render_to_string("admin/carcode/qr_print.html", {"car_codes": queryset})

        response = HttpResponse(html)
        response["Content-Disposition"] = 'inline; filename="qr_codes.html"'
        return response

    print_qr_codes.short_description = "Print QR Codes"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "print-qr/",
                self.admin_site.admin_view(self.print_qr_codes_view),
                name="print_qr_codes",
            ),
        ]
        return custom_urls + urls

    def print_qr_codes_view(self, request):
        selected_ids = request.GET.get("ids", "").split(",")
        queryset = self.get_queryset(request).filter(id__in=selected_ids)
        return self.print_qr_codes(request, queryset)

    def car_company_name(self, obj):
        if not obj.car:
            return ""
        return obj.car.branch.company.name

    car_company_name.short_description = "Company"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("car__branch__company")
            .order_by("-created")
        )


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "code",
        "lincense_number",
        "lincense_expiration_date",
        "branch",
        "company_name",
        "created_by",
        "updated_by",
        "created",
        "modified",
    )
    search_fields = (
        "name",
        "phone_number",
        "code",
        "lincense_number",
        "lincense_expiration_date",
        "branch__name",
    )
    list_filter = (
        "name",
        "phone_number",
        "code",
        "lincense_number",
        "lincense_expiration_date",
        "branch",
        "branch__company",
    )
    readonly_fields = ("code", "created_by", "updated_by")
    list_per_page = 10

    def company_name(self, obj):
        return obj.branch.company.name

    company_name.short_description = "Company"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "branch":
            kwargs["queryset"] = CompanyBranch.objects.order_by(
                "name"
            )  # Order countries alphabetically
            kwargs["empty_label"] = None  # Remove the empty option
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_fields(self, request, obj=None):
        """Hide 'created_by' field in the add form but show it in the edit form."""
        fields = super().get_fields(request, obj)
        if not obj:
            fields = [
                field
                for field in fields
                if field not in ["created_by", "updated_by", "code"]
            ]
        return fields

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new Driver.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()


@admin.register(CompanyCashRequest)
class CompanyCashRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "code",
        "company",
        "amount",
        "status",
        "otp",
        "driver",
        "station",
        "station_branch",
        "created_by",
        "updated_by",
        "created",
        "modified",
    )
    search_fields = (
        "company__name",
        "amount",
        "status",
        "driver__name",
        "station__name",
        "station_branch__name",
    )
    list_filter = ("company", "status", "driver", "station", "driver__branch")
    readonly_fields = ("created_by", "updated_by")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("driver__branch")

    def has_add_permission(self, request):
        pass

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == "in_progress":
            return True
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == "in_progress":
            return True
        return False

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new CarOperation.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()


class CreatedDateRangeFilter(admin.SimpleListFilter):
    title = _("Created Date Range")
    parameter_name = "created_range"
    template = "admin/caroperation_date_filter.html"

    date_parameters = ("created_from", "created_to")

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)
        # SimpleListFilter only consumes `parameter_name`; the extra range
        # params must be removed here or the changelist passes them to the ORM.
        for param in self.date_parameters:
            if param in params:
                value = params.pop(param)
                if isinstance(value, list):
                    value = value[-1] if value else ""
                self.used_parameters[param] = value

    def expected_parameters(self):
        return [self.parameter_name, *self.date_parameters]

    def lookups(self, request, model_admin):
        # required by Django admin, but not really used
        return (("custom", _("Custom range")),)

    def parsed_date(self, param):
        value = self.used_parameters.get(param)
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def start_of_day(value):
        return timezone.make_aware(datetime.combine(value, time.min))

    def queryset(self, request, queryset):
        start_date = self.parsed_date("created_from")
        end_date = self.parsed_date("created_to")

        # a half-open datetime range stays sargable; `created__date__gte` wraps
        # the column in a timezone conversion, which no index can serve
        if start_date:
            queryset = queryset.filter(created__gte=self.start_of_day(start_date))

        if end_date:
            queryset = queryset.filter(
                created__lt=self.start_of_day(end_date + timedelta(days=1))
            )

        return queryset


class StationBranchListFilter(admin.RelatedFieldListFilter):
    """
    `StationBranch.__str__` reads `station.name`, so the stock filter runs one
    query per option while building the dropdown. Build the choices from a
    single joined query instead.
    """

    def field_choices(self, field, request, model_admin):
        ordering = self.field_admin_ordering(field, request, model_admin)
        queryset = field.remote_field.model._default_manager.select_related("station")
        if ordering:
            queryset = queryset.order_by(*ordering)
        return [(branch.pk, str(branch)) for branch in queryset]


@admin.register(AIApiResponse)
class AIApiResponseAdmin(admin.ModelAdmin):
    list_display = (
        "get_station_branch",
        "image_preview",
        "car_operation_amount",
        "extracted_number",
        "match_score",
        "model_name",
        "request_time_display",
        "token_taken",
        "estimated_money_egp",
        "image_size_mb",
        "created",
    )
    search_fields = ("car_operation__code", "extracted_number", "model_name")
    list_filter = ("match_score", "model_name", "car_operation__station_branch")
    readonly_fields = (
        "created_by",
        "updated_by",
        "created",
        "modified",
        "match_score",
        "estimated_money_egp",
        "request_time_display",
    )
    list_per_page = 20
    autocomplete_fields = ("car_operation",)

    def get_changelist(self, request, **kwargs):
        from django.contrib.admin.views.main import ChangeList

        class PageSizeChangeList(ChangeList):
            def get_filters_params(self, params=None):
                lookup_params = super().get_filters_params(params)
                lookup_params.pop("page_size", None)
                return lookup_params

        return PageSizeChangeList

    def get_changelist_instance(self, request):
        original_list_per_page = self.list_per_page
        page_size = request.GET.get("page_size")
        if page_size and str(page_size).isdigit():
            self.list_per_page = min(int(page_size), 1000)
        try:
            return super().get_changelist_instance(request)
        finally:
            self.list_per_page = original_list_per_page

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "car_operation", "car_operation__station_branch"
        )

    def get_station_branch(self, obj):
        if obj.car_operation and obj.car_operation.station_branch:
            return obj.car_operation.station_branch
        return "-"
    get_station_branch.short_description = "Station Branch"

    def car_operation_amount(self, obj):
        if obj.car_operation:
            return obj.car_operation.amount
        return "-"
    car_operation_amount.short_description = "Amount"

    def image_preview(self, obj):
        if obj.car_operation and obj.car_operation.fuel_image:
            url = obj.car_operation.fuel_image.url
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">'
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />'
                "</a>",
                url,
                url,
            )
        return "-"
    image_preview.short_description = "Image"

    def image_size_mb(self, obj):
        if obj.image_size:
            try:
                size_mb = int(obj.image_size) / (1024 * 1024)
                return f"{size_mb:.2f} MB"
            except (ValueError, TypeError):
                return "-"
        return "-"
    image_size_mb.short_description = "Image Size (MB)"

    def estimated_money_egp(self, obj):
        if obj.estimated_money is None:
            return "-"
        return f"{obj.estimated_money:.2f} EGP"
    estimated_money_egp.short_description = "Estimated Money (EGP)"
    estimated_money_egp.admin_order_field = "estimated_money"

    def request_time_display(self, obj):
        if obj.request_time is None:
            return "-"
        return f"{obj.request_time:.2f}s"
    request_time_display.short_description = "Request Time"
    request_time_display.admin_order_field = "request_time"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

@admin.register(CarOperation)
class CarOperationAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        if obj and obj.status == "completed":
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        if obj.status == "completed":
            raise PermissionDenied("Cannot delete a completed operation.")
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        if queryset.filter(status="completed").exists():
            raise PermissionDenied("Cannot delete completed operations.")
        super().delete_queryset(request, queryset)

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the
        'created_by' when creating a new CarOperation.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        queryset = self.get_queryset(request)
        queryset = queryset.aggregate(
            total_cost=Sum("cost"), total_amount=Sum("amount")
        )
        extra_context["sum_cost"] = queryset["total_cost"] or 0
        extra_context["sum_amount"] = queryset["total_amount"] or 0
        return super().changelist_view(request, extra_context=extra_context)

    list_display = (
        "id",
        "code",
        "status",
        "start_time",
        "end_time",
        "duration",
        "cost",
        "station_cost",
        "company_cost",
        "profits",
        "amount",
        "unit",
        "car",
        "driver",
        "station_branch",
        "worker",
        "service",
        "branch_company",
    )
    search_fields = ("code", "car__code", "car__plate_number")
    list_filter = (
        "status",
        "start_time",
        "end_time",
        "car",
        "car__branch__company",
        "driver",
        "station_branch__station",
        "station_branch",
        "worker",
        "service",
    )

    readonly_fields = ("code", "created_by", "updated_by", "created")
    list_per_page = 20

    def branch_company(self, obj):
        return obj.car.branch.company.name

    branch_company.short_description = "Company"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "car__branch__company",
                "driver",
                "station_branch",
                "worker",
                "service",
                "created_by",
            )
        )

@admin.register(MonthlyInventory)
class MonthlyInventoryAdmin(CarOperationAdmin):
    list_display = (
        "id",
        "code",
        "amount",
        "profits",
        "station_branch",
        "service",
        "car",
        "branch_company",
    )
    list_filter = (
        CreatedDateRangeFilter,
        "status",
        "car__branch__company",
        ("station_branch", StationBranchListFilter),
        "service",
    )
    # skips the extra unfiltered COUNT(*) over the whole operations table
    show_full_result_count = False

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        # every relation touched by list_display, including the `station` that
        # StationBranch.__str__ reads
        return (
            super(CarOperationAdmin, self)
            .get_queryset(request)
            .select_related(
                "car__branch__company",
                "station_branch__station",
                "service",
            )
        )

    def changelist_view(self, request, extra_context=None):
        # skip CarOperationAdmin.changelist_view, which aggregates other columns
        response = super(CarOperationAdmin, self).changelist_view(
            request, extra_context
        )

        # reuse the ChangeList super() already built: asking for another one
        # re-runs the count and the page query. Redirects carry no context.
        changelist = getattr(response, "context_data", {}).get("cl")
        if changelist is None:
            return response

        # cl.queryset is filtered but unpaginated, so the totals match the filters
        totals = changelist.queryset.aggregate(
            total_amount=Sum("amount"),
            total_profits=Sum("profits"),
            total_company_cost=Sum("company_cost"),
            total_station_cost=Sum("station_cost"),
        )
        response.context_data.update(
            {
                "sum_amount": totals["total_amount"] or 0,
                "sum_profits": totals["total_profits"] or 0,
                "sum_company_cost": totals["total_company_cost"] or 0,
                "sum_station_cost": totals["total_station_cost"] or 0,
            }
        )
        return response
