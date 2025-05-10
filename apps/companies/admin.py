from django import forms
from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from apps.companies.models.operation_model import CarOperation

from .models.company_cash_models import CompanyCashRequest
from .models.company_models import Car, Company, CompanyBranch, Driver


class BranchInline(admin.TabularInline):
    model = CompanyBranch
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "address",
        "phone_number",
        "balance",
        "branches_link",
        "cars_link",
        "drivers_link",
        "district",
        "created_by",
        "updated_by",
    )
    search_fields = ("name", "address", "phone_number")
    readonly_fields = ["created_by", "updated_by"]
    list_per_page = 20
    # inlines = [BranchInline]

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

    drivers_link.short_description = "Drivers"
    cars_link.short_description = "Cars"
    branches_link.short_description = "Branches"


@admin.register(CompanyBranch)
class CompanyBranchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone_number",
        "company",
        "balance",
        "car_link",
        "driver_link",
        "district",
        "created_by",
        "updated_by",
    )
    search_fields = ("name", "email", "phone_number")
    list_filter = ("company",)
    readonly_fields = ["created_by", "updated_by"]
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
        obj.updated_by = request.user
        obj.save()


class CarForm(forms.ModelForm):
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
            "color": forms.TextInput(attrs={"type": "color"}),
        }

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
        "code",
    )
    list_per_page = 10

    def company_name(self, obj):
        return obj.branch.company.name

    company_name.short_description = "Company"

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
        "branch",
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
        "company",
        "amount",
        "status",
        "driver",
        "station",
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
    )
    list_filter = ("company", "status", "driver", "station")
    readonly_fields = ("created_by", "updated_by")


@admin.register(CarOperation)
class CarOperationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "status",
        "start_time",
        "end_time",
        "duration",
        "cost",
        "amount",
        "unit",
        "fuel_type",
        "car",
        "driver",
        "station_branch",
        "worker",
        "service",
        "branch_company",
    )
    search_fields = (
        "code",
        "worker",
        "service",
    )
    list_filter = (
        "status",
        "start_time",
        "end_time",
        "fuel_type",
        "car",
        "car__branch__company",
        "driver",
        "station_branch",
        "worker",
        "service",
    )
    readonly_fields = ("code", "created_by", "updated_by")
    list_per_page = 100

    def branch_company(self, obj):
        return obj.car.branch.company.name

    branch_company.short_description = "Company"
