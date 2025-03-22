from rest_framework.routers import DefaultRouter

from .views import CompanyBranchViewSet, CompanyViewSet, DriverViewSet

router = DefaultRouter()

router.register('company-branches', CompanyBranchViewSet, basename='company-branches')
router.register('drivers', DriverViewSet, basename='drivers')
router.register('', CompanyViewSet, basename='companies')

urlpatterns = router.urls
