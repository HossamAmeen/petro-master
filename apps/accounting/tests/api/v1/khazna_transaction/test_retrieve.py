import pytest
from rest_framework import status

from .helpers import transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionRetrieve:
    def test_retrieve_unauthenticated_fail(self, api_client, khazna_transaction_factory):
        tx = khazna_transaction_factory()

        response = api_client.get(transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_not_found_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(transaction_detail_url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_dashboard_user_success(
        self, auth_client, admin_user, khazna_transaction_factory
    ):
        tx = khazna_transaction_factory(description="a note")

        response = auth_client(admin_user).get(transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["amount"] == str(tx.amount)
        assert response.data["reference_code"] == tx.reference_code
        assert response.data["description"] == "a note"
        assert response.data["created_by"] == tx.created_by_id

    def test_retrieve_station_worker_success(
        self, auth_client, station_worker, branch, khazna_transaction_factory
    ):
        """Station roles are not scoped by `KhaznaTransactionViewSet`, so a
        worker can retrieve any transaction by id."""
        tx = khazna_transaction_factory()

        response = auth_client(station_worker, station_id=branch.station_id).get(
            transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
