import pytest
from rest_framework import status

from apps.companies.models.operation_model import CarOperation
from apps.companies.tests.api.v1.car_operation.helpers import operation_detail_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_delete_without_authentication_fail(api_client, car_operation_factory):
    operation = car_operation_factory()

    response = api_client.delete(operation_detail_url(operation.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert CarOperation.objects.filter(pk=operation.id).exists()


def test_delete_disallowed_for_authenticated_user_fail(
    auth_client, company_owner, company, car_operation_factory
):
    operation = car_operation_factory()

    response = auth_client(company_owner, company_id=company.id).delete(
        operation_detail_url(operation.id)
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "disallowed delete method"
    assert CarOperation.objects.filter(pk=operation.id).exists()


@pytest.mark.parametrize("role_fixture", ["admin_user", "station_worker"])
def test_delete_disallowed_for_other_roles_fail(
    role_fixture,
    request,
    auth_client,
    company,
    station,
    car_operation_factory,
):
    user = request.getfixturevalue(role_fixture)
    operation = car_operation_factory()
    client_kwargs = {}
    if role_fixture == "station_worker":
        client_kwargs["station_id"] = station.id

    response = auth_client(user, **client_kwargs).delete(
        operation_detail_url(operation.id)
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CarOperation.objects.filter(pk=operation.id).exists()
