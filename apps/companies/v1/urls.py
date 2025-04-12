from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CompanyBranchViewSet,
    CompanyCashRequestViewSet,
    CompanyViewSet,
    DriverViewSet,
)

router = DefaultRouter()

router.register("branches", CompanyBranchViewSet, basename="company-branches")
router.register("drivers", DriverViewSet, basename="drivers")
router.register(
    "cash-requests", CompanyCashRequestViewSet, basename="company-cash-requests"
)
router.register("", CompanyViewSet, basename="companies")

urlpatterns = router.urls

urlpatterns += [
    path(
        "branches/<int:pk>/assign-managers/",
        CompanyBranchViewSet.as_view({"post": "assign_managers"}),
        name="branch-assign-managers",
    )
]
