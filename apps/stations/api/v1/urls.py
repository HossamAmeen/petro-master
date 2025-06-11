from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.stations.api.v1.car_operations import StationGasOperationsAPIView
from apps.stations.api.v1.views.service_views import ServiceViewSet
from apps.stations.api.v1.views.station_branch_views import StationBranchViewSet
from apps.stations.api.v1.views.station_views import (
    StationHomeAPIView,
    StationOperationsAPIView,
    StationReportsAPIView,
    StationViewSet,
)

router = DefaultRouter()
router.register("branches", StationBranchViewSet, basename="station-branches")
router.register("stations", StationViewSet, basename="stations")
router.register("services", ServiceViewSet, basename="services")

urlpatterns = router.urls

urlpatterns += [
    path("home/", StationHomeAPIView.as_view(), name="station-home"),
    path("operations/", StationOperationsAPIView.as_view(), name="station-operations"),
    path(
        "gas-operations/",
        StationGasOperationsAPIView.as_view(),
        name="station-gas-operations",
    ),
    path("reports/", StationReportsAPIView.as_view(), name="station-reports"),
]
