import pytest
from rest_framework import status

from apps.users.models import User
from apps.users.tests.helpers import station_owners_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationOwnerRetrieve:

    def test_retrieve_without_authentication_fail(self, api_client, station_owner):
        response = api_client.get(station_owners_detail_url(station_owner.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_as_company_owner_fail(
        self, auth_client, company_owner, company, station_owner
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            station_owners_detail_url(station_owner.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_success(self, auth_client, admin_user, station_owner, station):
        response = auth_client(admin_user).get(
            station_owners_detail_url(station_owner.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == station_owner.id
        assert response.data["name"] == station_owner.name
        assert response.data["phone_number"] == station_owner.phone_number
        assert response.data["role"] == User.UserRoles.StationOwner
        assert response.data["station"] == {"id": station.id, "name": station.name}

    def test_retrieve_unknown_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(station_owners_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND
