import pytest
from rest_framework import status

from .helpers import transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionRetrieve:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, khazna_transaction_factory):
        self.auth_client = auth_client
        self.admin_client = auth_client(admin_user)
        self.create_transaction = khazna_transaction_factory

    def retrieve(self, pk, client=None):
        return (client or self.admin_client).get(transaction_detail_url(pk))

    def test_retrieve_unauthenticated_fail(self, api_client):
        tx = self.create_transaction()

        response = self.retrieve(tx.id, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_not_found_fail(self):
        response = self.retrieve(999999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_dashboard_user_success(self):
        tx = self.create_transaction(description="a note")

        response = self.retrieve(tx.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["amount"] == str(tx.amount)
        assert response.data["reference_code"] == tx.reference_code
        assert response.data["description"] == "a note"
        assert response.data["created_by"] == tx.created_by_id

    def test_retrieve_station_worker_success(self, station_worker, branch):
        """Station roles are not scoped by `KhaznaTransactionViewSet`, so a
        worker can retrieve any transaction by id."""
        tx = self.create_transaction()
        client = self.auth_client(station_worker, station_id=branch.station_id)

        response = self.retrieve(tx.id, client=client)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id

    def test_retrieve_customer_support_success(self, customer_support_user):
        tx = self.create_transaction()

        response = self.retrieve(tx.id, client=self.auth_client(customer_support_user))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
