from rest_framework.routers import DefaultRouter

from .api import CompanyBranchViewSet, CompanyViewSet, DriverViewSet
from .views import DriverViewSet

router = DefaultRouter()
router.register('drivers', DriverViewSet)
router.register('company-branches', CompanyBranchViewSet)
router.register('companies', CompanyViewSet)

urlpatterns = router.urls
