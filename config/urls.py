"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Petro Master API",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="example@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/users/', include('apps.users.v1.urls')),
    path('api/v1/companies/', include('apps.companies.v1.urls')),
    path('api/v1/stations/', include('apps.stations.v1.urls')),
    path('api/v1/notifications/', include('apps.notifications.v1.urls')),
    path('api/v1/auth/', include('apps.auth.v1.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
