from rest_framework.routers import DefaultRouter

from .views.company_users_view import CompanyBranchManagerViewSet
from .views.station_view import StationBranchManagerViewSet, StationOwnerViewSet
from .views.users_view import FirebaseTokenViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet)
router.register(
    "company-branch-managers",
    CompanyBranchManagerViewSet,
    basename="company-branch-managers",
)
router.register("firebase-tokens", FirebaseTokenViewSet, basename="firebase-tokens")
router.register("station-owners", StationOwnerViewSet, basename="station-owners")
router.register(
    "station-branch-managers",
    StationBranchManagerViewSet,
    basename="station-branch-managers",
)

urlpatterns = router.urls
