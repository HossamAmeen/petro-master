import pytest
from rest_framework import status

from apps.users.tests.helpers import returned_ids, workers_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestWorkerList:

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(workers_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_as_company_owner_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).get(
            workers_list_url()
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_as_driver_fail(self, auth_client, driver_user):
        response = auth_client(driver_user).get(workers_list_url())

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_as_admin_sees_all_success(
        self, auth_client, admin_user, station_worker, other_station_worker
    ):
        response = auth_client(admin_user).get(workers_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert {station_worker.id, other_station_worker.id}.issubset(ids)

    def test_list_as_station_owner_is_station_scoped_success(
        self, auth_client, station_owner, station, station_worker, other_station_worker
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            workers_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station_worker.id in ids
        assert other_station_worker.id not in ids

    def test_list_as_branch_manager_is_managed_branch_scoped_success(
        self,
        auth_client,
        branch_manager,
        station,
        station_worker,
        other_station_worker,
        admin_user,
        branch,
    ):
        from apps.stations.models.stations_models import StationBranch
        from apps.users.models import User, Worker

        unmanaged = StationBranch.objects.create(
            name="Unmanaged Branch",
            address="Addr",
            lang=31.2,
            lat=30.1,
            district=branch.district,
            station=station,
            created_by=admin_user,
        )
        unmanaged_worker = Worker.objects.create(
            name="Unmanaged Worker",
            phone_number="01600000030",
            email="unmanaged_worker@example.com",
            password="password123",
            role=User.UserRoles.StationWorker,
            station_branch=unmanaged,
            created_by=admin_user,
        )

        response = auth_client(branch_manager, station_id=station.id).get(
            workers_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station_worker.id in ids
        assert unmanaged_worker.id not in ids
        assert other_station_worker.id not in ids

    def test_list_filter_by_station_branch_success(
        self, auth_client, admin_user, branch, station_worker, other_station_worker
    ):
        response = auth_client(admin_user).get(
            workers_list_url(station_branch=branch.id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert station_worker.id in ids
        assert other_station_worker.id not in ids

    def test_list_payload_includes_nested_branch_success(
        self, auth_client, admin_user, station_worker, branch, station
    ):
        response = auth_client(admin_user).get(workers_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[station_worker.id]
        assert row["name"] == station_worker.name
        assert row["phone_number"] == station_worker.phone_number
        assert row["station_branch"]["id"] == branch.id
        assert row["station_branch"]["station"] == station.id
