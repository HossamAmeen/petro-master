from django.contrib import admin
from .models import Country, City, District
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')

class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'city')

admin.site.register(Country, CountryAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(District, DistrictAdmin)