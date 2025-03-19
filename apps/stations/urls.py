from rest_framework.routers import DefaultRouter

from apps.stations.views import StationViewSet

router = DefaultRouter()
router.register('stations', StationViewSet, basename='stations')
urlpatterns = router.urls
urlpatterns += []
