from rest_framework.routers import DefaultRouter

from .views.car_views import CarViewSet, DriverViewSet
from .views.company_cash_request_views import CompanyCashRequestViewSet
from .views.company_views import CompanyBranchViewSet, CompanyViewSet

router = DefaultRouter()

router.register("branches", CompanyBranchViewSet, basename="company-branches")
router.register("drivers", DriverViewSet, basename="drivers")
router.register("cars", CarViewSet, basename="cars")
router.register(
    "cash-requests", CompanyCashRequestViewSet, basename="company-cash-requests"
)
router.register("", CompanyViewSet, basename="companies")

urlpatterns = router.urls
