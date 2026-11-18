from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Car
from apps.utilities.testing import assert_soft_deleted, listed_ids

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def car_detail_url(car_id):
    return reverse("cars-detail", kwargs={"pk": car_id})


class TestCarDelete:

    def test_delete_without_authentication_fail(self, api_client, company_car):
        response = api_client.delete(car_detail_url(company_car.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Car.objects.filter(pk=company_car.id).exists()

    def test_delete_zero_balance_car_success(
        self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        response = auth_client(company_owner, company_id=company.id).delete(
            car_detail_url(company_car.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Car.objects.filter(pk=company_car.id).exists()

    def test_delete_positive_balance_car_fail(
        self,
        auth_client,
        company_owner,
        company,
        car_factory,
    ):
        car = car_factory(balance=Decimal("0.01"))

        response = auth_client(company_owner, company_id=company.id).delete(
            car_detail_url(car.id)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.filter(pk=car.id).exists()

    def test_delete_outside_company_scope_fail(
        self,
        auth_client,
        company_owner,
        company,
        car_factory,
        other_company_branch,
    ):
        other_car = car_factory(branch=other_company_branch)

        response = auth_client(company_owner, company_id=company.id).delete(
            car_detail_url(other_car.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Car.objects.filter(pk=other_car.id).exists()

    def test_delete_unknown_car_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).delete(car_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCarSoftDelete:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, company_owner, company, car_factory, car_code_factory):
        self.client = auth_client(company_owner, company_id=company.id)
        self.car_code = car_code_factory()
        self.car = car_factory(code=self.car_code.code)
        response = self.client.delete(car_detail_url(self.car.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_keeps_row_with_deleted_at_success(self):
        assert_soft_deleted(Car, self.car.id)

    def test_deleted_car_hidden_from_list_success(self):
        response = self.client.get(reverse("cars-list"))

        assert response.status_code == status.HTTP_200_OK
        assert self.car.id not in listed_ids(response)

    def test_retrieve_deleted_car_not_found_fail(self):
        response = self.client.get(car_detail_url(self.car.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_already_deleted_car_not_found_fail(self):
        response = self.client.delete(car_detail_url(self.car.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_with_deleted_car_code_fail(self, car_payload_factory):
        """The deleted car still holds its unique code in the database."""
        self.client.raise_request_exception = False

        response = self.client.post(
            reverse("cars-list"),
            car_payload_factory(car_code=self.car_code),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.all_objects.filter(code=self.car.code).count() == 1
