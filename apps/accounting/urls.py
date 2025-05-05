from rest_framework.routers import DefaultRouter
from .views import KhaznaTransactionViewSet

router = DefaultRouter()
router.register(r'khazna-transactions', KhaznaTransactionViewSet, basename='transaction')

urlpatterns = router.urls
