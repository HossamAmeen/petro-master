from rest_framework.routers import DefaultRouter

from apps.geo.v1.views import CityViewSet, DistrictViewSet

router = DefaultRouter()
router.register("cities", CityViewSet, basename="cities")
router.register("districts", DistrictViewSet, basename="districts")

urlpatterns = router.urls
