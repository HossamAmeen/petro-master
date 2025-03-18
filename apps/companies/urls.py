from rest_framework.routers import DefaultRouter

from .views import CompanyBranchViewSet, CompanyViewSet, DriverViewSet

router = DefaultRouter()
router.register('drivers', DriverViewSet)
router.register('company-branches', CompanyBranchViewSet)
router.register('companies', CompanyViewSet)

urlpatterns = router.urls
