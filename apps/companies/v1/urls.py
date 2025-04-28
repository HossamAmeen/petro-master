from rest_framework.routers import DefaultRouter

from apps.companies.v1.views.car_operation_views import CarOperationViewSet

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
router.register("car-operations", CarOperationViewSet, basename="car-operations")
router.register("", CompanyViewSet, basename="companies")

urlpatterns = router.urls
