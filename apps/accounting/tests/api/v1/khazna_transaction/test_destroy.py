import pytest
from rest_framework import status

from apps.accounting.models import KhaznaTransaction

from .helpers import transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionDestroy:
    """Unlike `CarOperationViewSet`, `KhaznaTransactionViewSet` does not
    disable deletion; any authenticated user can delete any transaction."""

    def test_destroy_unauthenticated_fail(self, api_client, khazna_transaction_factory):
        tx = khazna_transaction_factory()

        response = api_client.delete(transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert KhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_not_found_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).delete(transaction_detail_url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_dashboard_user_success(
        self, auth_client, admin_user, khazna_transaction_factory
    ):
        tx = khazna_transaction_factory()

        response = auth_client(admin_user).delete(transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not KhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_worker_can_delete_any_transaction_success(
        self, auth_client, station_worker, branch, khazna_transaction_factory
    ):
        tx = khazna_transaction_factory()

        response = auth_client(station_worker, station_id=branch.station_id).delete(
            transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
