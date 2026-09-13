from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.company_models import Car
from apps.companies.tests.api.v1.car.helpers import car_detail_url
from apps.companies.tests.helpers import set_balance


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCarUpdate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, company_owner, company, company_car):
        self.owner = company_owner
        self.car = company_car
        self.client = auth_client(company_owner, company_id=company.id)
        self.url = car_detail_url(company_car.id)

    def patch(self, payload):
        return self.client.patch(self.url, payload, format="json")

    def test_partial_update_without_authentication_fail(self, api_client):
        response = api_client.patch(self.url, {"brand": "Updated"}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_partial_update_company_car_success(self):
        response = self.patch({"brand": "Updated"})

        assert response.status_code == status.HTTP_200_OK
        self.car.refresh_from_db()
        assert self.car.brand == "Updated"
        assert self.car.updated_by_id == self.owner.id

    @pytest.mark.parametrize(
        ("restricted_field", "new_value"),
        [
            ("balance", "999.00"),
            ("is_blocked_balance_update", True),
            ("last_meter", 99_999),
            ("code", "RESTRICT01"),
        ],
    )
    def test_partial_update_company_restricted_field_ignored_success(
        self, restricted_field, new_value
    ):
        original_value = getattr(self.car, restricted_field)

        response = self.patch({restricted_field: new_value})

        assert response.status_code == status.HTTP_200_OK, response.data
        self.car.refresh_from_db()
        assert getattr(self.car, restricted_field) == original_value

    def test_partial_update_dashboard_balance_success(self, auth_client, admin_user):
        response = auth_client(admin_user).patch(
            self.url, {"balance": "125.50"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        self.car.refresh_from_db()
        assert self.car.balance == Decimal("125.50")

    def test_partial_update_outside_company_scope_fail(
        self, car_factory, other_company_branch
    ):
        other_car = car_factory(branch=other_company_branch)

        response = self.client.patch(
            car_detail_url(other_car.id), {"brand": "Forbidden"}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        other_car.refresh_from_db()
        assert other_car.brand != "Forbidden"

    def test_partial_update_permitted_fuel_above_capacity_fail(self):
        response = self.patch({"permitted_fuel_amount": self.car.tank_capacity + 1})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.car.refresh_from_db()
        assert self.car.permitted_fuel_amount <= self.car.tank_capacity

    def test_full_update_car_success(self, car_code_factory, car_payload_factory):
        car_code = car_code_factory(code=self.car.code)
        payload = car_payload_factory(
            car_code=car_code,
            code=self.car.code,
            branch=self.car.branch_id,
            brand="Fully Updated",
        )

        response = self.client.put(self.url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK, response.data
        self.car.refresh_from_db()
        assert self.car.brand == "Fully Updated"
        assert self.car.updated_by_id == self.owner.id

    def test_full_update_missing_required_field_fail(
        self, car_code_factory, car_payload_factory
    ):
        car_code = car_code_factory(code=self.car.code)
        payload = car_payload_factory(
            car_code=car_code, code=self.car.code, branch=self.car.branch_id
        )
        payload.pop("brand")

        response = self.client.put(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_partial_update_balance_source_on_empty_car_success(self, balance_source):
        set_balance(self.car, "0.00")

        response = self.patch({"balance_source": balance_source})

        assert response.status_code == status.HTTP_200_OK, response.data
        self.car.refresh_from_db()
        assert self.car.balance_source == balance_source

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_partial_update_balance_source_with_remaining_balance_fail(
        self, balance_source
    ):
        set_balance(self.car, "25.00")

        response = self.patch({"balance_source": balance_source})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.car.refresh_from_db()
        assert self.car.balance_source == Car.BalanceSource.CAR
        assert self.car.balance == Decimal("25.00")

    def test_partial_update_back_to_car_balance_source_success(self):
        self.car.balance_source = Car.BalanceSource.COMPANY
        self.car.save(update_fields=["balance_source"])

        response = self.patch({"balance_source": Car.BalanceSource.CAR})

        assert response.status_code == status.HTTP_200_OK, response.data
        self.car.refresh_from_db()
        assert self.car.balance_source == Car.BalanceSource.CAR

    def test_partial_update_keeps_balance_source_when_not_sent_success(self):
        self.car.balance_source = Car.BalanceSource.BRANCH
        set_balance(self.car, "0.00")
        self.car.save(update_fields=["balance_source"])

        response = self.patch({"brand": "Untouched Source"})

        assert response.status_code == status.HTTP_200_OK, response.data
        self.car.refresh_from_db()
        assert self.car.balance_source == Car.BalanceSource.BRANCH

    def test_partial_update_invalid_balance_source_fail(self):
        response = self.patch({"balance_source": "khazna"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.car.refresh_from_db()
        assert self.car.balance_source == Car.BalanceSource.CAR
