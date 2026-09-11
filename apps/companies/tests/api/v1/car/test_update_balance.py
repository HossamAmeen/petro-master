from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.models.company_models import Car
from apps.companies.tests.api.v1.car.helpers import update_balance_url
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification

pytestmark = [pytest.mark.api, pytest.mark.django_db]

NON_CAR_SOURCES = [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY]


class TestCarUpdateBalance:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, company_owner, company, company_car):
        self.company = company
        self.car = company_car
        self.client = auth_client(company_owner, company_id=company.id)
        self.url = update_balance_url(company_car.id)

    def update_balance(self, amount="10.00", type="add", client=None):
        return (client or self.client).post(
            self.url, {"amount": amount, "type": type}, format="json"
        )

    def set_balance_source(self, balance_source):
        self.car.balance_source = balance_source
        self.car.save(update_fields=["balance_source"])

    def test_update_balance_without_authentication_fail(self, api_client):
        response = self.update_balance(client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_balance_as_company_owner_success(self):
        set_balance(self.company, "100.00")

        response = self.update_balance("40.00", "add")

        assert response.status_code == status.HTTP_200_OK
        self.company.refresh_from_db()
        self.car.refresh_from_db()
        assert self.company.balance == Decimal("60.00")
        assert self.car.balance == Decimal("40.00")

    def test_add_balance_as_branch_manager_success(
        self, auth_client, company_branch_manager, company_branch
    ):
        set_balance(company_branch, "100.00")

        response = self.update_balance(
            "30.00",
            "add",
            client=auth_client(company_branch_manager, company_id=self.company.id),
        )

        assert response.status_code == status.HTTP_200_OK
        company_branch.refresh_from_db()
        self.car.refresh_from_db()
        assert company_branch.balance == Decimal("70.00")
        assert self.car.balance == Decimal("30.00")

    def test_subtract_balance_as_company_owner_success(self):
        set_balance(self.company, "100.00")
        set_balance(self.car, "50.00")

        response = self.update_balance("20.00", "subtract")

        assert response.status_code == status.HTTP_200_OK
        self.company.refresh_from_db()
        self.car.refresh_from_db()
        assert self.company.balance == Decimal("120.00")
        assert self.car.balance == Decimal("30.00")

    def test_add_balance_with_insufficient_parent_balance_fail(self):
        set_balance(self.company, "10.00")

        response = self.update_balance("10.01", "add")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.company.refresh_from_db()
        self.car.refresh_from_db()
        assert self.company.balance == Decimal("10.00")
        assert self.car.balance == Decimal("0.00")

    def test_subtract_balance_with_insufficient_car_balance_fail(self):
        set_balance(self.car, "10.00")

        response = self.update_balance("10.01", "subtract")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.car.refresh_from_db()
        assert self.car.balance == Decimal("10.00")

    def test_update_balance_for_blocked_car_fail(self):
        self.car.is_blocked_balance_update = True
        self.car.save(update_fields=["is_blocked_balance_update"])

        response = self.update_balance()

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "payload",
        [
            {"amount": "-1.00", "type": "add"},
            {"amount": "1.00", "type": "invalid"},
            {"type": "add"},
            {"amount": "1.00"},
        ],
    )
    def test_update_balance_with_invalid_payload_fail(self, payload):
        response = self.client.post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_balance_outside_company_scope_fail(
        self, car_factory, other_company_branch
    ):
        other_car = car_factory(branch=other_company_branch)

        response = self.client.post(
            update_balance_url(other_car.id),
            {"amount": "10.00", "type": "add"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("balance_source", NON_CAR_SOURCES)
    @pytest.mark.parametrize("operation_type", ["add", "subtract"])
    def test_update_balance_for_non_car_balance_source_fail(
        self, balance_source, operation_type, company_branch
    ):
        self.set_balance_source(balance_source)
        set_balance(self.company, "100.00")
        set_balance(company_branch, "100.00")

        response = self.update_balance("40.00", operation_type)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "balance_source_not_car"
        self.company.refresh_from_db()
        company_branch.refresh_from_db()
        self.car.refresh_from_db()
        assert self.company.balance == Decimal("100.00")
        assert company_branch.balance == Decimal("100.00")
        assert self.car.balance == Decimal("0.00")

    def test_update_balance_for_non_car_source_creates_no_transaction_fail(self):
        self.set_balance_source(Car.BalanceSource.COMPANY)
        set_balance(self.company, "100.00")

        response = self.update_balance("40.00", "add")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CompanyKhaznaTransaction.objects.count() == 0
        assert Notification.objects.count() == 0

    def test_update_balance_for_car_balance_source_success(self):
        self.set_balance_source(Car.BalanceSource.CAR)
        set_balance(self.company, "100.00")

        response = self.update_balance("40.00", "add")

        assert response.status_code == status.HTTP_200_OK, response.data
        self.company.refresh_from_db()
        self.car.refresh_from_db()
        assert self.company.balance == Decimal("60.00")
        assert self.car.balance == Decimal("40.00")

    def test_update_balance_blocked_check_runs_before_balance_source_check_fail(self):
        self.car.balance_source = Car.BalanceSource.BRANCH
        self.car.is_blocked_balance_update = True
        self.car.save(update_fields=["balance_source", "is_blocked_balance_update"])

        response = self.update_balance("40.00", "add")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_found"
