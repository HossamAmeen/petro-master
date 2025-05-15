from rest_framework.routers import DefaultRouter

from apps.accounting.v1.views import (
    CompanyKhaznaTransactionViewSet,
    KhaznaTransactionViewSet,
)

router = DefaultRouter()
router.register(
    r"khazna-transactions", KhaznaTransactionViewSet, basename="transaction"
)
router.register(
    r"company-khazna-transactions",
    CompanyKhaznaTransactionViewSet,
    basename="company-khazna-transactions",
)
urlpatterns = router.urls
