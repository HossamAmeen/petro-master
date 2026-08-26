import pytest
from rest_framework import status

from apps.users.models import StationOwner
from apps.users.tests.helpers import station_owners_detail_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_delete_without_authentication_fail(api_client, other_station_owner):
    response = api_client.delete(station_owners_detail_url(other_station_owner.id))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert StationOwner.objects.filter(pk=other_station_owner.id).exists()


def test_delete_as_driver_fail(auth_client, driver_user, other_station_owner):
    response = auth_client(driver_user).delete(
        station_owners_detail_url(other_station_owner.id)
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_delete_success(auth_client, admin_user, other_station_owner):
    user_id = other_station_owner.id

    response = auth_client(admin_user).delete(station_owners_detail_url(user_id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not StationOwner.objects.filter(pk=user_id).exists()
