import pytest
from rest_framework import status

from apps.accounting.models import KhaznaTransaction

from .helpers import transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionDestroy:
    """Unlike `CarOperationViewSet`, `KhaznaTransactionViewSet` does not
    disable deletion; any authenticated user can delete any transaction."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, khazna_transaction_factory):
        self.auth_client = auth_client
        self.admin_client = auth_client(admin_user)
        self.create_transaction = khazna_transaction_factory

    def destroy(self, pk, client=None):
        return (client or self.admin_client).delete(transaction_detail_url(pk))

    def test_destroy_unauthenticated_fail(self, api_client):
        tx = self.create_transaction()

        response = self.destroy(tx.id, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert KhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_not_found_fail(self):
        response = self.destroy(999999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_dashboard_user_success(self):
        tx = self.create_transaction()

        response = self.destroy(tx.id)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not KhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_worker_can_delete_any_transaction_success(
        self, station_worker, branch
    ):
        tx = self.create_transaction()
        client = self.auth_client(station_worker, station_id=branch.station_id)

        response = self.destroy(tx.id, client=client)

        assert response.status_code == status.HTTP_204_NO_CONTENT
