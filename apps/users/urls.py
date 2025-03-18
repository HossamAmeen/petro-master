from django.urls import path

from .views import LoginAPIView, UserViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('users', UserViewSet)

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
] + router.urls
