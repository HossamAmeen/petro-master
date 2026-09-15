from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.notifications.models import Notification

from .helpers import company_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyKhaznaTransactionUpdate:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        self.auth_client = auth_client
        self.admin_client = auth_client(admin_user)
        self.company = company
        self.company_branch = company_branch
        self.create_transaction = company_transaction_factory

    def update(self, pk, payload, client=None):
        return (client or self.admin_client).patch(
            company_transaction_detail_url(pk), payload, format="json"
        )

    def own_transaction(self, **overrides):
        return self.create_transaction(
            company=self.company, company_branch=self.company_branch, **overrides
        )

    def full_payload(self, status, company_branch=None):
        return {
            "company": self.company.id,
            "company_branch": (company_branch or self.company_branch).id,
            "status": status,
        }

    def test_update_unauthenticated_fail(self, api_client):
        tx = self.own_transaction(status="pending")

        response = self.update(tx.id, {"status": "approved"}, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_station_role_forbidden_fail(self, station_worker, branch):
        tx = self.own_transaction(status="pending")
        client = self.auth_client(station_worker, station_id=branch.station_id)

        response = self.update(tx.id, {"status": "approved"}, client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_not_found_fail(self):
        response = self.update(999999, {"status": "approved"})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_omitting_company_branch_raises_keyerror_fail(self):
        """Documents actual (buggy) behavior: `UpdateCompanyKhaznaTransactionSerializer.validate`
        indexes `attrs["company_branch"]` unconditionally. On a partial update
        that omits `company_branch` (e.g. `{"status": "approved"}`, the typical
        approve/decline payload), `attrs` has no such key and the view raises
        an unhandled `KeyError` instead of returning a clean validation error."""
        tx = self.own_transaction(status="pending")

        with pytest.raises(KeyError):
            self.update(tx.id, {"status": "approved"})

    def test_update_full_payload_status_to_approved_success(
        self, company_branch_manager
    ):
        self.company_branch.balance = Decimal("100.00")
        self.company_branch.save(update_fields=["balance"])
        tx = self.own_transaction(
            status="pending", amount=Decimal("40.00"), is_incoming=True
        )

        response = self.update(tx.id, self.full_payload("approved"))

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        self.company_branch.refresh_from_db()
        assert tx.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED
        assert self.company_branch.balance == Decimal("60.00")
        notification = Notification.objects.get(user_id=company_branch_manager.id)
        assert notification.type == Notification.NotificationType.MONEY

    def test_update_already_approved_fail(self):
        tx = self.own_transaction(status="approved")

        response = self.update(tx.id, self.full_payload("declined"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "لا يمكن اتمام عملية هيا منهيه بالفعل"

    def test_update_already_declined_fail(self):
        tx = self.own_transaction(status="declined")

        response = self.update(tx.id, self.full_payload("approved"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "لا يمكن اتمام عملية هيا منهيه بالفعل"

    def test_update_company_branch_mismatch_fail(self, other_company_branch):
        tx = self.own_transaction(status="pending")

        response = self.update(
            tx.id, self.full_payload("approved", company_branch=other_company_branch)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "الشركة غير مطابقة للفرع"

    def test_update_company_owner_cannot_update_other_company_transaction_fail(
        self, company_owner, other_company, other_company_branch
    ):
        tx = self.create_transaction(
            company=other_company, company_branch=other_company_branch, status="pending"
        )
        client = self.auth_client(company_owner, company_id=self.company.id)

        response = self.update(
            tx.id,
            {
                "company": other_company.id,
                "company_branch": other_company_branch.id,
                "status": "approved",
            },
            client=client,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_status_to_declined_does_not_touch_balance_or_notify_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_branch_manager,
        company_transaction_factory,
    ):
        company_branch.balance = Decimal("100.00")
        company_branch.save(update_fields=["balance"])
        tx = company_transaction_factory(
            company=company,
            company_branch=company_branch,
            status="pending",
            amount=Decimal("40.00"),
            is_incoming=True,
        )

        response = auth_client(admin_user).patch(
            company_transaction_detail_url(tx.id),
            {
                "company": company.id,
                "company_branch": company_branch.id,
                "status": "declined",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        tx.refresh_from_db()
        company_branch.refresh_from_db()
        assert tx.status == CompanyKhaznaTransaction.TransactionStatus.DECLINED
        assert tx.updated_by_id == admin_user.id
        assert company_branch.balance == Decimal("100.00")
        assert not Notification.objects.exists()

    def test_put_bypasses_finalized_guard_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        """Documents actual (buggy) behavior: PUT maps to the `update` action, which
        `get_serializer_class` does not handle, so it falls back to the read
        serializer (`fields = "__all__"`). That skips
        `UpdateCompanyKhaznaTransactionSerializer`, letting a client rewrite an
        already approved transaction (amount and status) without any balance
        reversal. PATCH correctly rejects the same change."""
        company_branch.balance = Decimal("60.00")
        company_branch.save(update_fields=["balance"])
        tx = company_transaction_factory(
            company=company,
            company_branch=company_branch,
            status="approved",
            amount=Decimal("40.00"),
            is_incoming=True,
        )

        response = auth_client(admin_user).put(
            company_transaction_detail_url(tx.id),
            {
                "company": company.id,
                "company_branch": company_branch.id,
                "amount": "999.00",
                "reference_code": tx.reference_code,
                "created_by": admin_user.id,
                "status": "pending",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        tx.refresh_from_db()
        company_branch.refresh_from_db()
        assert tx.amount == Decimal("999.00")
        assert tx.status == CompanyKhaznaTransaction.TransactionStatus.PENDING
        assert company_branch.balance == Decimal("60.00")

    def test_update_finance_success(self, finance_user):
        tx = self.own_transaction(status="pending")

        response = self.update(
            tx.id,
            self.full_payload("declined"),
            client=self.auth_client(finance_user),
        )

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        assert tx.status == CompanyKhaznaTransaction.TransactionStatus.DECLINED
        assert tx.updated_by_id == finance_user.id

    @pytest.mark.parametrize("method", ["patch", "put"])
    def test_update_customer_support_fail(self, method, customer_support_user):
        self.company_branch.balance = Decimal("100.00")
        self.company_branch.save(update_fields=["balance"])
        tx = self.own_transaction(
            status="pending", amount=Decimal("40.00"), is_incoming=True
        )
        client = self.auth_client(customer_support_user)

        response = getattr(client, method)(
            company_transaction_detail_url(tx.id),
            self.full_payload("approved"),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        tx.refresh_from_db()
        self.company_branch.refresh_from_db()
        assert tx.status == CompanyKhaznaTransaction.TransactionStatus.PENDING
        assert self.company_branch.balance == Decimal("100.00")
        assert not Notification.objects.exists()
