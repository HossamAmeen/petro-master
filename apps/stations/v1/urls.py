from rest_framework.routers import DefaultRouter

from apps.stations.v1.views import StationBranchViewSet, StationViewSet

router = DefaultRouter()

router.register("", StationViewSet, basename="stations")
router.register("branches", StationBranchViewSet, basename="station-branches")

urlpatterns = router.urls
