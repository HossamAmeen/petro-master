from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def update_balance_url(car_id):
    return reverse("cars-update_balance", kwargs={"pk": car_id})


def set_balance(instance, amount):
    instance.balance = Decimal(amount)
    instance.save(update_fields=["balance"])


class TestCarUpdateBalance:


    def test_update_balance_without_authentication_fail(self, api_client, company_car):
        response = api_client.post(
            update_balance_url(company_car.id),
            {"amount": "10.00", "type": "add"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_add_balance_as_company_owner_success(self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        set_balance(company, "100.00")

        response = auth_client(company_owner, company_id=company.id).post(
            update_balance_url(company_car.id),
            {"amount": "40.00", "type": "add"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        company.refresh_from_db()
        company_car.refresh_from_db()
        assert company.balance == Decimal("60.00")
        assert company_car.balance == Decimal("40.00")


    def test_add_balance_as_branch_manager_success(self,
        auth_client,
        company_branch_manager,
        company,
        company_branch,
        company_car,
    ):
        set_balance(company_branch, "100.00")

        response = auth_client(company_branch_manager, company_id=company.id).post(
            update_balance_url(company_car.id),
            {"amount": "30.00", "type": "add"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        company_branch.refresh_from_db()
        company_car.refresh_from_db()
        assert company_branch.balance == Decimal("70.00")
        assert company_car.balance == Decimal("30.00")


    def test_subtract_balance_as_company_owner_success(self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        set_balance(company, "100.00")
        set_balance(company_car, "50.00")

        response = auth_client(company_owner, company_id=company.id).post(
            update_balance_url(company_car.id),
            {"amount": "20.00", "type": "subtract"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        company.refresh_from_db()
        company_car.refresh_from_db()
        assert company.balance == Decimal("120.00")
        assert company_car.balance == Decimal("30.00")


    def test_add_balance_with_insufficient_parent_balance_fail(self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        set_balance(company, "10.00")

        response = auth_client(company_owner, company_id=company.id).post(
            update_balance_url(company_car.id),
            {"amount": "10.01", "type": "add"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        company.refresh_from_db()
        company_car.refresh_from_db()
        assert company.balance == Decimal("10.00")
        assert company_car.balance == Decimal("0.00")


    def test_subtract_balance_with_insufficient_car_balance_fail(self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        set_balance(company_car, "10.00")

        response = auth_client(company_owner, company_id=company.id).post(
            update_balance_url(company_car.id),
            {"amount": "10.01", "type": "subtract"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        company_car.refresh_from_db()
        assert company_car.balance == Decimal("10.00")


    def test_update_balance_for_blocked_car_fail(self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        company_car.is_blocked_balance_update = True
        company_car.save(update_fields=["is_blocked_balance_update"])

        response = auth_client(company_owner, company_id=company.id).post(
            update_balance_url(company_car.id),
            {"amount": "10.00", "type": "add"},
            format="json",
        )

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
    def test_update_balance_with_invalid_payload_fail(self,
        payload,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        response = auth_client(company_owner, company_id=company.id).post(
            update_balance_url(company_car.id),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


    def test_update_balance_outside_company_scope_fail(self,
        auth_client,
        company_owner,
        company,
        car_factory,
        other_company_branch,
    ):
        other_car = car_factory(branch=other_company_branch)

        response = auth_client(company_owner, company_id=company.id).post(
            update_balance_url(other_car.id),
            {"amount": "10.00", "type": "add"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
