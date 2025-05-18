from rest_framework.routers import DefaultRouter

from apps.stations.v1.views import ServiceViewSet, StationBranchViewSet, StationViewSet

router = DefaultRouter()
router.register("branches", StationBranchViewSet, basename="station-branches")
router.register("stations", StationViewSet, basename="stations")
router.register("services", ServiceViewSet, basename="services")

urlpatterns = router.urls
