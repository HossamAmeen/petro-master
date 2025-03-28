from django.contrib import admin

# Register your models here.
from .models.stations_models import Service, Station, StationBranch, StationService

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'unit', 'cost', 'created_by')  # Display in list view
    list_filter = ('type', 'unit')  # Filter sidebar
    search_fields = ('name',)  # Search by name
    readonly_fields = ('created_by', 'updated_by')  # Hide created_by from the form

    def save_model(self, request, obj, form, change):
        """Assign the logged-in user to created_by before saving."""
        if not obj.pk:  # Only set created_by on creation, not updates
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Station)
admin.site.register(StationService)
admin.site.register(StationBranch)
