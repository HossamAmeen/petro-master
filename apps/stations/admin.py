from django.contrib import admin

# Register your models here.
from .models.stations_models import Station, StationBranch, StationService

admin.site.register(Station)
admin.site.register(StationService)
admin.site.register(StationBranch)
