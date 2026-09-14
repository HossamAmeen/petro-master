import pytest
from rest_framework import status

from apps.users.tests.helpers import station_owners_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationOwnerUpdate:

    def test_update_without_authentication_fail(self, api_client, station_owner):
        response = api_client.patch(
            station_owners_detail_url(station_owner.id),
            {"name": "Hacker"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_as_company_owner_fail(
        self, auth_client, company_owner, company, station_owner
    ):
        response = auth_client(company_owner, company_id=company.id).patch(
            station_owners_detail_url(station_owner.id),
            {"name": "Nope"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        station_owner.refresh_from_db()
        assert station_owner.name != "Nope"

    def test_update_name_success(self, auth_client, admin_user, station_owner):
        response = auth_client(admin_user).patch(
            station_owners_detail_url(station_owner.id),
            {"name": "Updated Station Owner"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        station_owner.refresh_from_db()
        assert station_owner.name == "Updated Station Owner"
