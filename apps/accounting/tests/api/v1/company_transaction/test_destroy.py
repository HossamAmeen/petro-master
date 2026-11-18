from decimal import Decimal
from unittest.mock import patch

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, KhaznaTransaction
from apps.utilities.testing import assert_soft_deleted, listed_ids

from .helpers import (
    company_transaction_detail_url,
    company_transaction_list_url,
    create_payload,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyKhaznaTransactionDestroy:
    """No action-level permission override exists for `destroy`, so it falls
    back to the viewset's default `EitherPermission([CompanyPermission,
    DashboardPermission])` and the same queryset scoping as list/retrieve."""

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

    def destroy(self, pk, client=None):
        return (client or self.admin_client).delete(company_transaction_detail_url(pk))

    def own_transaction(self, **overrides):
        return self.create_transaction(
            company=self.company, company_branch=self.company_branch, **overrides
        )

    def test_destroy_unauthenticated_fail(self, api_client):
        tx = self.own_transaction()

        response = self.destroy(tx.id, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_role_forbidden_fail(self, station_worker, branch):
        tx = self.own_transaction()
        client = self.auth_client(station_worker, station_id=branch.station_id)

        response = self.destroy(tx.id, client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_destroy_dashboard_user_success(self):
        tx = self.own_transaction()

        response = self.destroy(tx.id)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_company_owner_can_delete_own_company_transaction_success(
        self, company_owner
    ):
        tx = self.own_transaction()
        client = self.auth_client(company_owner, company_id=self.company.id)

        response = self.destroy(tx.id, client=client)

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_company_owner_cannot_delete_other_company_transaction_fail(
        self, company_owner, other_company, other_company_branch
    ):
        tx = self.create_transaction(
            company=other_company, company_branch=other_company_branch
        )
        client = self.auth_client(company_owner, company_id=self.company.id)

        response = self.destroy(tx.id, client=client)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_does_not_reverse_balance_success(self):
        """Deleting an approved transaction does not refund the balance
        change it caused; balance mutation only happens on create/update."""
        self.company_branch.balance = Decimal("50.00")
        self.company_branch.save(update_fields=["balance"])
        tx = self.own_transaction(status="approved", amount=Decimal("20.00"))

        response = self.destroy(tx.id)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.company_branch.refresh_from_db()
        assert self.company_branch.balance == Decimal("50.00")

    def test_destroy_finance_fail(self, finance_user):
        tx = self.own_transaction()

        response = self.destroy(tx.id, client=self.auth_client(finance_user))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_customer_support_fail(self, customer_support_user):
        tx = self.own_transaction()

        response = self.destroy(tx.id, client=self.auth_client(customer_support_user))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()


class TestCompanyKhaznaTransactionSoftDelete:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        auth_client,
        admin_user,
        company,
        company_branch,
        company_transaction_factory,
    ):
        self.client = auth_client(admin_user)
        self.company = company
        self.company_branch = company_branch
        self.tx = company_transaction_factory(reference_code="111111")
        response = self.client.delete(company_transaction_detail_url(self.tx.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(CompanyKhaznaTransaction, self.tx.id)
        assert_soft_deleted(KhaznaTransaction, self.tx.id)

    def test_deleted_transaction_hidden_from_list_success(self):
        response = self.client.get(company_transaction_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert self.tx.id not in listed_ids(response)

    def test_retrieve_deleted_transaction_not_found_fail(self):
        response = self.client.get(company_transaction_detail_url(self.tx.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_transaction_not_found_fail(self):
        response = self.client.delete(company_transaction_detail_url(self.tx.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("apps.shared.generate_code.random.randint", side_effect=[111111, 222222])
    def test_create_skips_reference_code_of_deleted_transaction_success(self, randint):
        """The deleted row keeps its unique `reference_code`, so the generator
        must not hand that code out again."""
        response = self.client.post(
            company_transaction_list_url(),
            create_payload(self.company, self.company_branch),
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = CompanyKhaznaTransaction.objects.get(id=response.data["id"])
        assert created.reference_code == "222222"
