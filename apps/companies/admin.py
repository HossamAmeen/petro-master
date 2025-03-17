from django.contrib import admin
from .models import Company, CompanyBranch, Car
from django import forms
from django.core.exceptions import ValidationError


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
                print(day)
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


admin.site.register(Company, CompanyAdmin)
admin.site.register(CompanyBranch, CompanyBranchAdmin)
admin.site.register(Car, CarAdmin)
