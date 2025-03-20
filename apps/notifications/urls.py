from rest_framework.routers import DefaultRouter

from apps.notifications.views import NotificationViewSet

router = DefaultRouter()
router.register('notifications', NotificationViewSet)
urlpatterns = router.urls
