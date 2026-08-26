import pytest
from rest_framework import status

from apps.users.tests.helpers import (
    returned_ids,
    station_branch_managers_list_url,
)


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationBranchManagerList:


    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(station_branch_managers_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_list_as_company_owner_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).get(
            station_branch_managers_list_url()
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


    def test_list_as_station_owner_is_station_scoped_success(self,
        auth_client,
        station_owner,
        station,
        branch_manager,
        other_station,
        admin_user,
    ):
        from apps.users.models import StationOwner, User

        other_manager = StationOwner.objects.create(
            name="Other Station Manager",
            phone_number="01600000020",
            email="other_station_manager@example.com",
            password="password123",
            role=User.UserRoles.StationBranchManager,
            station=other_station,
            created_by=admin_user,
        )

        response = auth_client(station_owner, station_id=station.id).get(
            station_branch_managers_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert branch_manager.id in ids
        assert other_manager.id not in ids


    def test_list_as_dashboard_sees_all_success(self,
        auth_client, admin_user, branch_manager, other_station, station
    ):
        from apps.users.models import StationOwner, User

        other_manager = StationOwner.objects.create(
            name="Other Station Manager",
            phone_number="01600000021",
            email="other_station_manager2@example.com",
            password="password123",
            role=User.UserRoles.StationBranchManager,
            station=other_station,
            created_by=admin_user,
        )

        response = auth_client(admin_user).get(
            station_branch_managers_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert {branch_manager.id, other_manager.id}.issubset(ids)


    def test_list_payload_includes_station_and_branches_success(self,
        auth_client, admin_user, branch_manager, station, branch
    ):
        response = auth_client(admin_user).get(
            station_branch_managers_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[branch_manager.id]
        assert row["name"] == branch_manager.name
        assert row["station"] == {"id": station.id, "name": station.name}
        assert any(item["id"] == branch.id for item in row["station_branches"])
