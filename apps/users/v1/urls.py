from rest_framework.routers import DefaultRouter

from apps.users.v1.views.agent_views import SupervisorViewSet

from .views.company_users_view import CompanyBranchManagerViewSet
from .views.station_users_view import (
    StationBranchManagerViewSet,
    StationOwnerViewSet,
    WorkerViewSet,
)
from .views.users_view import FirebaseTokenViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("supervisors", SupervisorViewSet, basename="supervisors")
router.register(
    "company-branch-managers",
    CompanyBranchManagerViewSet,
    basename="company-branch-managers",
)
router.register("firebase-tokens", FirebaseTokenViewSet, basename="firebase-tokens")
router.register("station-owners", StationOwnerViewSet, basename="station-owners")
router.register("workers", WorkerViewSet, basename="workers")
router.register(
    "station-branch-managers",
    StationBranchManagerViewSet,
    basename="station-branch-managers",
)

urlpatterns = router.urls
