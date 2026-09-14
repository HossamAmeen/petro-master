import pytest
from rest_framework import status

from apps.accounting.models import KhaznaTransaction

from .helpers import transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestKhaznaTransactionCreate:
    """`KhaznaTransactionSerializer` uses `fields = "__all__"` and the
    viewset does not mix in `InjectUserMixin`, so `created_by` must be
    supplied explicitly by the client instead of being derived from the
    request user."""

    @pytest.fixture(autouse=True)
    def setup(self, auth_client, admin_user):
        self.auth_client = auth_client
        self.admin = admin_user
        self.admin_client = auth_client(admin_user)
        self.url = transaction_list_url()

    def base_payload(self, **overrides):
        payload = {
            "amount": "10.00",
            "reference_code": "NEWREF001",
            "is_incoming": True,
            "created_by": self.admin.id,
        }
        payload.update(overrides)
        return payload

    def create(self, payload, client=None):
        return (client or self.admin_client).post(self.url, payload, format="json")

    def test_create_unauthenticated_fail(self, api_client):
        response = self.create(self.base_payload(), client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_success(self):
        response = self.create(self.base_payload())

        assert response.status_code == status.HTTP_201_CREATED
        assert KhaznaTransaction.objects.filter(reference_code="NEWREF001").exists()
        assert response.data["created_by"] == self.admin.id
        assert response.data["status"] == KhaznaTransaction.TransactionStatus.PENDING

    def test_create_missing_created_by_fail(self):
        payload = self.base_payload()
        payload.pop("created_by")

        response = self.create(payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "created_by"

    def test_create_duplicate_reference_code_fail(self, khazna_transaction_factory):
        existing = khazna_transaction_factory(reference_code="DUPLICATE")

        response = self.create(
            self.base_payload(reference_code=existing.reference_code)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "reference_code"

    def test_create_missing_amount_fail(self):
        payload = self.base_payload()
        payload.pop("amount")

        response = self.create(payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "amount"

    def test_create_station_worker_can_create_success(self, station_worker, branch):
        """Permission is `IsAuthenticated` only; any authenticated role,
        including station workers, may create a base khazna transaction."""
        client = self.auth_client(station_worker, station_id=branch.station_id)

        response = self.create(
            self.base_payload(reference_code="WORKERREF"), client=client
        )

        assert response.status_code == status.HTTP_201_CREATED
