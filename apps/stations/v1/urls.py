from rest_framework.routers import DefaultRouter

from apps.stations.v1.views import StationBranchViewSet, StationViewSet

router = DefaultRouter()
router.register("branches", StationBranchViewSet, basename="station-branches")
router.register("", StationViewSet, basename="stations")

urlpatterns = router.urls
