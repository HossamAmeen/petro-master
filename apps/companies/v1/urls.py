from rest_framework.routers import DefaultRouter

from .views import (
    CarViewSet,
    CompanyBranchViewSet,
    CompanyCashRequestViewSet,
    CompanyViewSet,
    DriverViewSet,
)

router = DefaultRouter()


router.register("branches", CompanyBranchViewSet, basename="company-branches")
router.register("drivers", DriverViewSet, basename="drivers")
router.register("cars", CarViewSet, basename="cars")
router.register(
    "cash-requests", CompanyCashRequestViewSet, basename="company-cash-requests"
)
router.register("", CompanyViewSet, basename="companies")

urlpatterns = router.urls
