import pytest
from django.urls import reverse
from rest_framework import status


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def car_detail_url(car_id):
    return reverse("cars-detail", kwargs={"pk": car_id})


class TestCarRetrieve:


    def test_retrieve_without_authentication_fail(self, api_client, company_car):
        response = api_client.get(car_detail_url(company_car.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_retrieve_owned_car_success(self,
        auth_client,
        company_owner,
        company,
        company_car,
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            car_detail_url(company_car.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == company_car.id
        assert response.data["code"] == company_car.code
        assert response.data["branch"]["id"] == company_car.branch_id


    def test_retrieve_outside_company_scope_fail(self,
        auth_client,
        company_owner,
        company,
        car_factory,
        other_company_branch,
    ):
        other_car = car_factory(branch=other_company_branch)

        response = auth_client(company_owner, company_id=company.id).get(
            car_detail_url(other_car.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


    def test_retrieve_unknown_car_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(car_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
