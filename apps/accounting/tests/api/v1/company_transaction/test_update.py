from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.notifications.models import Notification

from .helpers import company_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyKhaznaTransactionUpdate:
    def test_update_unauthenticated_fail(
        self, api_client, company, company_branch, company_transaction_factory
    ):
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, status="pending"
        )

        response = api_client.patch(
            company_transaction_detail_url(tx.id), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_station_role_forbidden_fail(
        self,
        auth_client,
        station_worker,
        branch,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, status="pending"
        )

        response = auth_client(station_worker, station_id=branch.station_id).patch(
            company_transaction_detail_url(tx.id), {"status": "approved"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_not_found_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).patch(
            company_transaction_detail_url(999999),
            {"status": "approved"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_omitting_company_branch_raises_keyerror_fail(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        """Documents actual (buggy) behavior: `UpdateCompanyKhaznaTransactionSerializer.validate`
        indexes `attrs["company_branch"]` unconditionally. On a partial update
        that omits `company_branch` (e.g. `{"status": "approved"}`, the typical
        approve/decline payload), `attrs` has no such key and the view raises
        an unhandled `KeyError` instead of returning a clean validation error."""
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, status="pending"
        )

        with pytest.raises(KeyError):
            auth_client(admin_user).patch(
                company_transaction_detail_url(tx.id),
                {"status": "approved"},
                format="json",
            )

    def test_update_full_payload_status_to_approved_success(
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
                "status": "approved",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        tx.refresh_from_db()
        company_branch.refresh_from_db()
        assert tx.status == CompanyKhaznaTransaction.TransactionStatus.APPROVED
        assert company_branch.balance == Decimal("60.00")
        notification = Notification.objects.get(user_id=company_branch_manager.id)
        assert notification.type == Notification.NotificationType.MONEY

    def test_update_already_approved_fail(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, status="approved"
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

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "لا يمكن اتمام عملية هيا منهيه بالفعل"

    def test_update_already_declined_fail(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, status="declined"
        )

        response = auth_client(admin_user).patch(
            company_transaction_detail_url(tx.id),
            {
                "company": company.id,
                "company_branch": company_branch.id,
                "status": "approved",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "لا يمكن اتمام عملية هيا منهيه بالفعل"

    def test_update_company_branch_mismatch_fail(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        other_company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=company, company_branch=company_branch, status="pending"
        )

        response = auth_client(admin_user).patch(
            company_transaction_detail_url(tx.id),
            {
                "company": company.id,
                "company_branch": other_company_branch.id,
                "status": "approved",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "الشركة غير مطابقة للفرع"

    def test_update_company_owner_cannot_update_other_company_transaction_fail(
        self,
        auth_client,
        company_owner,
        company,
        other_company,
        other_company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=other_company, company_branch=other_company_branch, status="pending"
        )

        response = auth_client(company_owner, company_id=company.id).patch(
            company_transaction_detail_url(tx.id),
            {
                "company": other_company.id,
                "company_branch": other_company_branch.id,
                "status": "approved",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
