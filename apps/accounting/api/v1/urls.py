from rest_framework.routers import DefaultRouter

from apps.accounting.api.v1.views import (
    CompanyKhaznaTransactionViewSet,
    KhaznaTransactionViewSet,
    StationKhaznaTransactionViewSet,
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
router.register(
    r"station-khazna-transactions",
    StationKhaznaTransactionViewSet,
    basename="station-khazna-transactions",
)

urlpatterns = router.urls
