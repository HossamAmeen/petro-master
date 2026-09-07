import pytest
from rest_framework import status

from .helpers import station_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionRetrieve:
    def test_retrieve_unauthenticated_fail(self, api_client, station_transaction_factory):
        tx = station_transaction_factory()

        response = api_client.get(station_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_not_found_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).get(station_transaction_detail_url(999999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_company_role_forbidden_fail(
        self, auth_client, company_owner, company, station_transaction_factory
    ):
        tx = station_transaction_factory()

        response = auth_client(company_owner, company_id=company.id).get(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_dashboard_user_success(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        tx = station_transaction_factory(station=station, station_branch=branch)

        response = auth_client(admin_user).get(station_transaction_detail_url(tx.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["station"] == {"id": station.id, "name": station.name}
        assert response.data["station_branch"]["id"] == branch.id
        assert response.data["reference_code"] == tx.reference_code

    def test_retrieve_station_owner_success(
        self, auth_client, station_owner, station, branch, station_transaction_factory
    ):
        tx = station_transaction_factory(station=station, station_branch=branch)

        response = auth_client(station_owner, station_id=station.id).get(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id

    def test_retrieve_station_owner_cannot_see_other_station_transaction_fail(
        self,
        auth_client,
        station_owner,
        station,
        other_station,
        other_station_branch,
        station_transaction_factory,
    ):
        tx = station_transaction_factory(
            station=other_station, station_branch=other_station_branch
        )

        response = auth_client(station_owner, station_id=station.id).get(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_station_worker_cannot_see_transaction_created_by_another_user_fail(
        self,
        auth_client,
        station_worker,
        station,
        branch,
        admin_user,
        station_transaction_factory,
    ):
        tx = station_transaction_factory(
            station=station, station_branch=branch, created_by=admin_user
        )

        response = auth_client(station_worker, station_id=station.id).get(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_station_worker_own_transaction_success(
        self, auth_client, station_worker, station, branch, station_transaction_factory
    ):
        tx = station_transaction_factory(
            station=station, station_branch=branch, created_by=station_worker
        )

        response = auth_client(station_worker, station_id=station.id).get(
            station_transaction_detail_url(tx.id)
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
