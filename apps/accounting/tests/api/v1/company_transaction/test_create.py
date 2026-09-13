from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.notifications.models import Notification

from .helpers import company_transaction_list_url, create_payload

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyKhaznaTransactionCreate:
    def test_create_unauthenticated_fail(self, api_client, company, company_branch):
        response = api_client.post(
            company_transaction_list_url(),
            create_payload(company, company_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_station_role_forbidden_fail(
        self, auth_client, station_worker, branch, company, company_branch
    ):
        response = auth_client(station_worker, station_id=branch.station_id).post(
            company_transaction_list_url(),
            create_payload(company, company_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_dashboard_user_success(
        self, auth_client, admin_user, company, company_branch
    ):
        response = auth_client(admin_user).post(
            company_transaction_list_url(),
            create_payload(company, company_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        tx = CompanyKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.company_id == company.id
        assert tx.company_branch_id == company_branch.id

    def test_create_company_owner_success(
        self, auth_client, company_owner, company, company_branch
    ):
        response = auth_client(company_owner, company_id=company.id).post(
            company_transaction_list_url(),
            create_payload(company, company_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_company_branch_manager_success(
        self, auth_client, company_branch_manager, company, company_branch
    ):
        response = auth_client(company_branch_manager, company_id=company.id).post(
            company_transaction_list_url(),
            create_payload(company, company_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_missing_company_branch_fail(
        self, auth_client, admin_user, company, company_branch
    ):
        """`company_branch` is redeclared with `required=True` on the create
        serializer even though the model field allows null, so branch-less
        (company-level) charges cannot be created through this endpoint."""
        payload = create_payload(company, company_branch)
        payload.pop("company_branch")

        response = auth_client(admin_user).post(
            company_transaction_list_url(), payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "company_branch"

    def test_create_company_branch_mismatch_fail(
        self, auth_client, admin_user, company, other_company_branch
    ):
        response = auth_client(admin_user).post(
            company_transaction_list_url(),
            create_payload(company, other_company_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["message"] == "الشركة غير مطابقة للفرع"

    def test_create_missing_amount_fail(
        self, auth_client, admin_user, company, company_branch
    ):
        payload = create_payload(company, company_branch)
        payload.pop("amount")

        response = auth_client(admin_user).post(
            company_transaction_list_url(), payload, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["errors"][0]["field"] == "amount"

    def test_create_ignores_client_supplied_reference_code_success(
        self, auth_client, admin_user, company, company_branch
    ):
        response = auth_client(admin_user).post(
            company_transaction_list_url(),
            create_payload(company, company_branch, reference_code="CLIENT-SET"),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        tx = CompanyKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.reference_code != "CLIENT-SET"

    def test_create_ignores_client_supplied_created_by_success(
        self,
        auth_client,
        admin_user,
        finance_user,
        company,
        company_branch,
    ):
        response = auth_client(admin_user).post(
            company_transaction_list_url(),
            create_payload(company, company_branch, created_by=finance_user.id),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        tx = CompanyKhaznaTransaction.objects.get(id=response.data["id"])
        assert tx.created_by_id == admin_user.id

    def test_create_pending_does_not_touch_balance_or_notify_success(
        self, auth_client, admin_user, company, company_branch
    ):
        company_branch.balance = Decimal("100.00")
        company_branch.save(update_fields=["balance"])
        notifications_before = Notification.objects.count()

        response = auth_client(admin_user).post(
            company_transaction_list_url(),
            create_payload(company, company_branch, status="pending", amount="10.00"),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        company_branch.refresh_from_db()
        assert company_branch.balance == Decimal("100.00")
        assert Notification.objects.count() == notifications_before

    def test_create_approved_deducts_branch_balance_and_notifies_manager_success(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_branch_manager,
    ):
        company_branch.balance = Decimal("100.00")
        company_branch.save(update_fields=["balance"])

        response = auth_client(admin_user).post(
            company_transaction_list_url(),
            create_payload(
                company,
                company_branch,
                status="approved",
                is_incoming=True,
                amount="30.00",
            ),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        company_branch.refresh_from_db()
        assert company_branch.balance == Decimal("70.00")
        notification = Notification.objects.get(user_id=company_branch_manager.id)
        assert notification.type == Notification.NotificationType.MONEY
        assert company_branch.name in notification.title

    def test_create_approved_outgoing_credits_branch_balance_success(
        self, auth_client, admin_user, company, company_branch
    ):
        company_branch.balance = Decimal("100.00")
        company_branch.save(update_fields=["balance"])

        response = auth_client(admin_user).post(
            company_transaction_list_url(),
            create_payload(
                company,
                company_branch,
                status="approved",
                is_incoming=False,
                amount="30.00",
            ),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        company_branch.refresh_from_db()
        assert company_branch.balance == Decimal("130.00")
