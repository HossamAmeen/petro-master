from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.companies.models.operation_model import CarOperation
from config.admin import custom_admin_site

from .models.company_cash_models import CompanyCashRequest
from .models.company_models import Car, Company, CompanyBranch, Driver


class BranchInline(admin.TabularInline):
    model = CompanyBranch
    extra = 0


@admin.register(Company, site=custom_admin_site)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "phone_number", "balance", "branches_link")
    search_fields = ("name", "address", "phone_number")
    list_per_page = 20
    inlines = [BranchInline]

    def branches_link(self, obj):
        count = obj.branches.count()
        url = (
            reverse("admin:companies_companybranch_changelist")
            + f"?company__id__exact={obj.id}"
        )
        return format_html('<a class="button" href="{}">Branches ({})</a>', url, count)

    branches_link.short_description = "Branches"


@admin.register(CompanyBranch, site=custom_admin_site)
class CompanyBranchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone_number",
        "company",
        "balance",
        "car_link",
        "driver_link",
    )
    search_fields = ("name", "email", "phone_number")
    list_filter = ("company",)
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


@admin.register(Car, site=custom_admin_site)
class CarAdmin(admin.ModelAdmin):
    form = CarForm
    list_display = (
        "code",
        "plate_number",
        "plate_character",
        "plate_color",
        "color",
        "license_expiration_date",
        "model_year",
        "brand",
        "is_with_odometer",
        "tank_capacity",
        "permitted_fuel_amount",
        "fuel_type",
        "number_of_fuelings_per_day",
        "fuel_allowed_days",
        "balance",
        "city",
        "branch",
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
    )
    readonly_fields = ("balance",)
    list_per_page = 10


@admin.register(Driver, site=custom_admin_site)
class DriverAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "phone_number",
        "code",
        "lincense_number",
        "lincense_expiration_date",
        "branch",
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
    )
    readonly_fields = ("code", "created_by", "updated_by")

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


@admin.register(CompanyCashRequest, site=custom_admin_site)
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


@admin.register(CarOperation, site=custom_admin_site)
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
