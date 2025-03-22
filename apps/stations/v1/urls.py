from rest_framework.routers import DefaultRouter

from apps.stations.v1.views import StationViewSet

router = DefaultRouter()
router.register('', StationViewSet, basename='stations')
urlpatterns = router.urls
