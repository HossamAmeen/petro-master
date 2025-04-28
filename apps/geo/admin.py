from django.contrib import admin

from .models import City, Country, District

admin.site.site_header = "Geo Management"
admin.site.index_title = "Manage Geo Data"


class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "country")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "country":
            kwargs["queryset"] = Country.objects.order_by(
                "name"
            )  # Order countries alphabetically
            kwargs["empty_label"] = None  # Remove the empty option
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "city")


admin.site.register(City, CityAdmin)
admin.site.register(District, DistrictAdmin)
