"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/users/', include('apps.users.v1.urls')),
    path('api/v1/companies/', include('apps.companies.v1.urls')),
    path('api/v1/stations/', include('apps.stations.v1.urls')),
    path('api/v1/notifications/', include('apps.notifications.v1.urls')),
    path('api/v1/auth/', include('apps.auth.v1.urls')),

    # swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
