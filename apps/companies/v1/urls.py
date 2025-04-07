from rest_framework.routers import DefaultRouter

from .views import CompanyBranchViewSet, CompanyViewSet, DriverViewSet, CompanyCashRequestViewSet

router = DefaultRouter()

router.register('branches', CompanyBranchViewSet, basename='company-branches')
router.register('drivers', DriverViewSet, basename='drivers')
router.register('cash-requests', CompanyCashRequestViewSet, basename='company-cash-requests')
router.register('', CompanyViewSet, basename='companies')

urlpatterns = router.urls
