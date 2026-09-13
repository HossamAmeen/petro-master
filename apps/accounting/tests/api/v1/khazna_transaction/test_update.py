import pytest
from rest_framework import status

from apps.accounting.models import KhaznaTransaction

from .helpers import transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionUpdate:
    """The base serializer is a plain `ModelSerializer` with no `validate`
    override and no balance side effects, unlike the company/station child
    serializers."""

    def test_update_unauthenticated_fail(self, api_client, khazna_transaction_factory):
        tx = khazna_transaction_factory()

        response = api_client.patch(
            transaction_detail_url(tx.id), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_not_found_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).patch(
            transaction_detail_url(999999), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_status_success(
        self, auth_client, admin_user, khazna_transaction_factory
    ):
        tx = khazna_transaction_factory(status=KhaznaTransaction.TransactionStatus.PENDING)

        response = auth_client(admin_user).patch(
            transaction_detail_url(tx.id), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        assert tx.status == KhaznaTransaction.TransactionStatus.APPROVED

    def test_update_can_be_reopened_after_approval_success(
        self, auth_client, admin_user, khazna_transaction_factory
    ):
        """No guard against re-editing an already approved/declined base
        transaction (that guard only exists on the company/station child
        serializers)."""
        tx = khazna_transaction_factory(
            status=KhaznaTransaction.TransactionStatus.APPROVED
        )

        response = auth_client(admin_user).patch(
            transaction_detail_url(tx.id), {"status": "pending"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        assert tx.status == KhaznaTransaction.TransactionStatus.PENDING

    def test_update_duplicate_reference_code_fail(
        self, auth_client, admin_user, khazna_transaction_factory
    ):
        khazna_transaction_factory(reference_code="TAKEN")
        tx = khazna_transaction_factory(reference_code="FREE")

        response = auth_client(admin_user).patch(
            transaction_detail_url(tx.id), {"reference_code": "TAKEN"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "reference_code"
