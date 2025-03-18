from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import LoginAPIView, UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet)

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
] + router.urls
