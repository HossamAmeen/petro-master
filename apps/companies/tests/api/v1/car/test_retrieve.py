import pytest
from rest_framework import status

from apps.companies.models.company_models import Car
from apps.companies.tests.api.v1.car.helpers import car_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCarRetrieve:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, company_owner, company, company_car):
        self.car = company_car
        self.client = auth_client(company_owner, company_id=company.id)
        self.url = car_detail_url(company_car.id)

    def test_retrieve_without_authentication_fail(self, api_client):
        response = api_client.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_owned_car_success(self):
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.car.id
        assert response.data["code"] == self.car.code
        assert response.data["branch"]["id"] == self.car.branch_id

    def test_retrieve_outside_company_scope_fail(
        self, car_factory, other_company_branch
    ):
        other_car = car_factory(branch=other_company_branch)

        response = self.client.get(car_detail_url(other_car.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_unknown_car_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(car_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "balance_source",
        [Car.BalanceSource.CAR, Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY],
    )
    def test_retrieve_exposes_balance_source_success(self, balance_source):
        self.car.balance_source = balance_source
        self.car.save(update_fields=["balance_source"])

        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["balance_source"] == balance_source
