from rest_framework.routers import DefaultRouter

from .views import CompanyBranchManagerViewSet, UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet)
router.register('company-branch-managers', CompanyBranchManagerViewSet, basename='company-branch-managers')

urlpatterns = router.urls
