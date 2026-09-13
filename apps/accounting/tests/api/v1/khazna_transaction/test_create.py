import pytest
from rest_framework import status

from apps.accounting.models import KhaznaTransaction

from .helpers import transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def base_payload(admin_user, **overrides):
    payload = {
        "amount": "10.00",
        "reference_code": "NEWREF001",
        "is_incoming": True,
        "created_by": admin_user.id,
    }
    payload.update(overrides)
    return payload


class TestKhaznaTransactionCreate:
    """`KhaznaTransactionSerializer` uses `fields = "__all__"` and the
    viewset does not mix in `InjectUserMixin`, so `created_by` must be
    supplied explicitly by the client instead of being derived from the
    request user."""

    def test_create_unauthenticated_fail(self, api_client, admin_user):
        response = api_client.post(
            transaction_list_url(), base_payload(admin_user), format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_success(self, auth_client, admin_user):
        response = auth_client(admin_user).post(
            transaction_list_url(), base_payload(admin_user), format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert KhaznaTransaction.objects.filter(reference_code="NEWREF001").exists()
        assert response.data["created_by"] == admin_user.id
        assert response.data["status"] == KhaznaTransaction.TransactionStatus.PENDING

    def test_create_missing_created_by_fail(self, auth_client, admin_user):
        payload = base_payload(admin_user)
        payload.pop("created_by")

        response = auth_client(admin_user).post(
            transaction_list_url(), payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "created_by"

    def test_create_duplicate_reference_code_fail(
        self, auth_client, admin_user, khazna_transaction_factory
    ):
        existing = khazna_transaction_factory(reference_code="DUPLICATE")

        response = auth_client(admin_user).post(
            transaction_list_url(),
            base_payload(admin_user, reference_code=existing.reference_code),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "reference_code"

    def test_create_missing_amount_fail(self, auth_client, admin_user):
        payload = base_payload(admin_user)
        payload.pop("amount")

        response = auth_client(admin_user).post(
            transaction_list_url(), payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "amount"

    def test_create_station_worker_can_create_success(
        self, auth_client, station_worker, branch, admin_user
    ):
        """Permission is `IsAuthenticated` only; any authenticated role,
        including station workers, may create a base khazna transaction."""
        response = auth_client(station_worker, station_id=branch.station_id).post(
            transaction_list_url(),
            base_payload(admin_user, reference_code="WORKERREF"),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
