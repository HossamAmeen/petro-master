from django import forms
from django.contrib import admin

from .models import Car, Company, CompanyBranch, Driver


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'phone_number')
    search_fields = ('name', 'address', 'phone_number')
    list_filter = ('name', 'address', 'phone_number')

class CompanyBranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number')
    search_fields = ('name', 'email', 'phone_number')
    list_filter = ('name', 'email', 'phone_number')



class CarForm(forms.ModelForm):
    fuel_allowed_days = forms.MultipleChoiceField(
        choices=Car.FuelAllowedDay.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Car
        fields = '__all__'
        widgets = {
            'fuel_allowed_days': forms.CheckboxSelectMultiple(choices=Car.FuelAllowedDay.choices),
        }

    def clean_fuel_allowed_days(self):
        fuel_allowed_days = self.cleaned_data.get('fuel_allowed_days')
        if not fuel_allowed_days:
            return []
        # Ensure that the input values are valid choices by checking against FuelAllowedDay
        valid_choices = dict(Car.FuelAllowedDay.choices)
        for day in fuel_allowed_days:
            if day not in valid_choices:
                raise forms.ValidationError(f"{day} is not a valid choice.")
        return fuel_allowed_days

    

class CarAdmin(admin.ModelAdmin):
    form = CarForm
    list_display = ('code', 'plate', 'color', 'license_expiration_date', 'model_year', 'brand',
                    'is_with_odometer', 'tank_capacity', 'permitted_fuel_amount', 'fuel_type',
                    'number_of_fuelings_per_day', 'fuel_allowed_days', 'balance', 'city', 'branch')
    search_fields = ('code', 'plate', 'color', 'license_expiration_date', 'model_year', 'brand',
                    'is_with_odometer', 'tank_capacity', 'permitted_fuel_amount', 'fuel_type',
                    'number_of_fuelings_per_day', 'fuel_allowed_days', 'balance', 'city', 'branch')
    list_filter = ('code', 'plate', 'color', 'license_expiration_date', 'model_year', 'brand',
                    'is_with_odometer', 'tank_capacity', 'permitted_fuel_amount', 'fuel_type',
                    'number_of_fuelings_per_day', 'fuel_allowed_days', 'balance', 'city', 'branch')
    readonly_fields = ('balance',)

class DriverAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'code', 'lincense_number', 'lincense_expiration_date', 'branch', 'created_by', 'updated_by', 'created', 'modified')
    search_fields = ('name', 'phone_number', 'code', 'lincense_number', 'lincense_expiration_date', 'branch')
    list_filter = ('name', 'phone_number', 'code', 'lincense_number', 'lincense_expiration_date', 'branch')
    readonly_fields = ('code', 'created_by', 'updated_by')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "branch":
            kwargs["queryset"] = CompanyBranch.objects.order_by('name')  # Order countries alphabetically
            kwargs["empty_label"] = None  # Remove the empty option
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_fields(self, request, obj=None):
        """ Hide 'created_by' field in the add form but show it in the edit form. """
        fields = super().get_fields(request, obj)
        if not obj:  # If creating a new Driver (obj is None), remove 'created_by'
            fields = [field for field in fields if field not in ["created_by", "updated_by", 'code']]
        return fields

    def save_model(self, request, obj, form, change):
        """
        Automatically assign the logged-in user as the 'created_by' when creating a new Driver.
        """
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()

admin.site.register(Company, CompanyAdmin)
admin.site.register(CompanyBranch, CompanyBranchAdmin)
admin.site.register(Car, CarAdmin)
admin.site.register(Driver, DriverAdmin)
