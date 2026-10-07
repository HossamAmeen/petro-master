import pytest
from rest_framework import status

from apps.accounting.models import KhaznaTransaction

from .helpers import transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionUpdate:
    """The base serializer is a plain `ModelSerializer` with no `validate`
    override and no balance side effects, unlike the company/station child
    serializers."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user, khazna_transaction_factory):
        self.admin_client = auth_client(admin_user)
        self.create_transaction = khazna_transaction_factory

    def update(self, pk, payload, client=None):
        return (client or self.admin_client).patch(
            transaction_detail_url(pk), payload, format="json"
        )

    def test_update_unauthenticated_fail(self, api_client):
        tx = self.create_transaction()

        response = self.update(tx.id, {"status": "approved"}, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_not_found_fail(self):
        response = self.update(999999, {"status": "approved"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_status_success(self):
        tx = self.create_transaction(status=KhaznaTransaction.TransactionStatus.PENDING)

        response = self.update(tx.id, {"status": "approved"})

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        assert tx.status == KhaznaTransaction.TransactionStatus.APPROVED

    def test_update_can_be_reopened_after_approval_success(self):
        """No guard against re-editing an already approved/declined base
        transaction (that guard only exists on the company/station child
        serializers)."""
        tx = self.create_transaction(
            status=KhaznaTransaction.TransactionStatus.APPROVED
        )

        response = self.update(tx.id, {"status": "pending"})

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        assert tx.status == KhaznaTransaction.TransactionStatus.PENDING

    def test_update_duplicate_reference_code_fail(self):
        self.create_transaction(reference_code="TAKEN")
        tx = self.create_transaction(reference_code="FREE")

        response = self.update(tx.id, {"reference_code": "TAKEN"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "reference_code"

    @pytest.mark.parametrize("method", ["patch", "put"])
    def test_update_customer_support_fail(
        self, method, auth_client, customer_support_user
    ):
        tx = self.create_transaction(status=KhaznaTransaction.TransactionStatus.PENDING)
        client = auth_client(customer_support_user)

        response = getattr(client, method)(
            transaction_detail_url(tx.id),
            {"amount": tx.amount, "created_by": tx.created_by_id, "status": "approved"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        tx.refresh_from_db()
        assert tx.status == KhaznaTransaction.TransactionStatus.PENDING
