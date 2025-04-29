from rest_framework.routers import DefaultRouter

from .views.company_users_view import CompanyBranchManagerViewSet
from .views.users_view import FirebaseTokenViewSet, UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet)
router.register(
    "company-branch-managers",
    CompanyBranchManagerViewSet,
    basename="company-branch-managers",
)
router.register("firebase-tokens", FirebaseTokenViewSet, basename="firebase-tokens")

urlpatterns = router.urls
