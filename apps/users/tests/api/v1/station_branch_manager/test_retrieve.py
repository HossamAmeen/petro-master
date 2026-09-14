import pytest
from rest_framework import status

from apps.users.models import StationBranchManager, StationOwner
from apps.users.tests.helpers import station_branch_managers_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationBranchManagerRetrieve:

    def test_retrieve_without_authentication_fail(self, api_client, branch_manager):
        response = api_client.get(station_branch_managers_detail_url(branch_manager.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_as_company_owner_fail(
        self, auth_client, company_owner, company, branch_manager
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            station_branch_managers_detail_url(branch_manager.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_success(
        self, auth_client, admin_user, branch_manager, station, branch
    ):
        response = auth_client(admin_user).get(
            station_branch_managers_detail_url(branch_manager.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == branch_manager.id
        assert response.data["name"] == branch_manager.name
        assert response.data["station"] == {"id": station.id, "name": station.name}
        assert any(
            item["id"] == branch.id for item in response.data["station_branches"]
        )

    def test_retrieve_other_station_as_owner_fail(
        self, auth_client, station_owner, station, other_station, admin_user
    ):
        from apps.users.models import User

        other_manager = StationOwner.objects.create(
            name="Foreign Manager",
            phone_number="01600000022",
            email="foreign_manager@example.com",
            password="password123",
            role=User.UserRoles.StationBranchManager,
            station=other_station,
            created_by=admin_user,
        )

        response = auth_client(station_owner, station_id=station.id).get(
            station_branch_managers_detail_url(other_manager.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_name_success(self, auth_client, admin_user, branch_manager):
        response = auth_client(admin_user).patch(
            station_branch_managers_detail_url(branch_manager.id),
            {"name": "Updated Station Manager"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        branch_manager.refresh_from_db()
        assert branch_manager.name == "Updated Station Manager"

    def test_update_replaces_station_branches_success(
        self, auth_client, admin_user, branch_manager, branch, station
    ):
        response = auth_client(admin_user).patch(
            station_branch_managers_detail_url(branch_manager.id),
            {"station_id": station.id, "station_branches": [branch.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assigned = set(
            StationBranchManager.objects.filter(user=branch_manager).values_list(
                "station_branch_id", flat=True
            )
        )
        assert assigned == {branch.id}

    def test_update_password_mismatch_fail(
        self, auth_client, admin_user, branch_manager
    ):
        response = auth_client(admin_user).patch(
            station_branch_managers_detail_url(branch_manager.id),
            {"password": "new-pass-123", "confirm_password": "other-pass"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_success(self, auth_client, admin_user, other_station, station):
        from apps.users.models import User

        manager = StationOwner.objects.create(
            name="Deletable Manager",
            phone_number="01600000023",
            email="deletable_manager@example.com",
            password="password123",
            role=User.UserRoles.StationBranchManager,
            station=other_station,
            created_by=admin_user,
        )

        response = auth_client(admin_user).delete(
            station_branch_managers_detail_url(manager.id)
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not StationOwner.objects.filter(pk=manager.id).exists()
