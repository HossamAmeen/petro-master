from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.companies.api.v1.views.car_operation_views import CarOperationViewSet

from .views.car_views import CarDetailsView, CarViewSet, DriverViewSet, VerifyDriverView
from .views.company_cash_request_views import CompanyCashRequestViewSet
from .views.company_views import CompanyBranchViewSet, CompanyHomeView, CompanyViewSet

router = DefaultRouter()

router.register("branches", CompanyBranchViewSet, basename="company-branches")
router.register("drivers", DriverViewSet, basename="drivers")
router.register("cars", CarViewSet, basename="cars")
router.register(
    "cash-requests", CompanyCashRequestViewSet, basename="company-cash-requests"
)
router.register("car-operations", CarOperationViewSet, basename="car-operations")


router.register("companies", CompanyViewSet, basename="companies")

urlpatterns = router.urls

urlpatterns += [
    path("home/", CompanyHomeView.as_view(), name="company-home"),
    path("car-details/<str:car_code>/", CarDetailsView.as_view(), name="car-details"),
    path(
        "verify-driver/<str:driver_code>/<str:car_code>/",
        VerifyDriverView.as_view(),
        name="verify-driver",
    ),
]
