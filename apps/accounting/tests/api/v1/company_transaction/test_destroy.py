import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction

from .helpers import company_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyKhaznaTransactionDestroy:
    """No action-level permission override exists for `destroy`, so it falls
    back to the viewset's default `EitherPermission([CompanyPermission,
    DashboardPermission])` and the same queryset scoping as list/retrieve."""

    def test_destroy_unauthenticated_fail(
        self, api_client, company, company_branch, company_transaction_factory
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = api_client.delete(company_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_station_role_forbidden_fail(
        self,
        auth_client,
        station_worker,
        branch,
        company,
        company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = auth_client(station_worker, station_id=branch.station_id).delete(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_destroy_dashboard_user_success(
        self, auth_client, admin_user, company, company_branch, company_transaction_factory
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = auth_client(admin_user).delete(company_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_company_owner_can_delete_own_company_transaction_success(
        self, auth_client, company_owner, company, company_branch, company_transaction_factory
    ):
        tx = company_transaction_factory(company=company, company_branch=company_branch)

        response = auth_client(company_owner, company_id=company.id).delete(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_destroy_company_owner_cannot_delete_other_company_transaction_fail(
        self,
        auth_client,
        company_owner,
        company,
        other_company,
        other_company_branch,
        company_transaction_factory,
    ):
        tx = company_transaction_factory(
            company=other_company, company_branch=other_company_branch
        )

        response = auth_client(company_owner, company_id=company.id).delete(
            company_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert CompanyKhaznaTransaction.objects.filter(id=tx.id).exists()

    def test_destroy_does_not_reverse_balance_success(
        self, auth_client, admin_user, company, company_branch, company_transaction_factory
    ):
        """Deleting an approved transaction does not refund the balance
        change it caused; balance mutation only happens on create/update."""
        from decimal import Decimal

        company_branch.balance = Decimal("50.00")
        company_branch.save(update_fields=["balance"])
        tx = company_transaction_factory(
            company=company,
            company_branch=company_branch,
            status="approved",
            amount=Decimal("20.00"),
        )

        response = auth_client(admin_user).delete(company_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        company_branch.refresh_from_db()
        assert company_branch.balance == Decimal("50.00")
