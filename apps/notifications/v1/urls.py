from rest_framework.routers import DefaultRouter

from apps.notifications.v1.views import NotificationViewSet

router = DefaultRouter()
router.register("", NotificationViewSet)
urlpatterns = router.urls
