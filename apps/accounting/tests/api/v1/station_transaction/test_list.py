import pytest
from rest_framework import status

from .helpers import station_transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {row["id"] for row in response.data["results"]}


class TestStationKhaznaTransactionList:
    def test_list_unauthenticated_fail(self, api_client):
        response = api_client.get(station_transaction_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_company_role_forbidden_fail(self, auth_client, company_owner, company):
        response = auth_client(company_owner, company_id=company.id).get(
            station_transaction_list_url()
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_dashboard_user_success(
        self, auth_client, admin_user, station_transaction_factory
    ):
        tx = station_transaction_factory()

        response = auth_client(admin_user).get(station_transaction_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert tx.id in returned_ids(response)

    def test_list_serializer_shape_success(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        tx = station_transaction_factory(station=station, station_branch=branch)

        response = auth_client(admin_user).get(station_transaction_list_url())

        item = next(row for row in response.data["results"] if row["id"] == tx.id)
        assert item["station"] == {"id": station.id, "name": station.name}
        assert item["station_branch"]["id"] == branch.id
        assert item["station_branch"]["name"] == branch.name

    def test_list_station_owner_scoped_to_own_station_success(
        self,
        auth_client,
        station_owner,
        station,
        branch,
        other_station,
        other_station_branch,
        station_transaction_factory,
    ):
        own_tx = station_transaction_factory(station=station, station_branch=branch)
        other_tx = station_transaction_factory(
            station=other_station, station_branch=other_station_branch
        )

        response = auth_client(station_owner, station_id=station.id).get(
            station_transaction_list_url()
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_station_branch_manager_sees_whole_station_not_just_managed_branch_success(
        self,
        auth_client,
        branch_manager,
        station,
        branch,
        second_station_branch,
        station_transaction_factory,
    ):
        """Documents actual behavior: the queryset filter
        `station__branches__managers__user` matches on the *station* having
        any branch managed by this user, not on the specific managed branch.
        So a branch manager sees every transaction for the whole station,
        including branches they do not manage (unlike
        `CompanyBranchManager`, which is scoped per-branch)."""
        managed_branch_tx = station_transaction_factory(station=station, station_branch=branch)
        other_branch_tx = station_transaction_factory(
            station=station, station_branch=second_station_branch
        )

        response = auth_client(branch_manager, station_id=station.id).get(
            station_transaction_list_url()
        )

        ids = returned_ids(response)
        assert managed_branch_tx.id in ids
        assert other_branch_tx.id in ids

    def test_list_station_branch_manager_excludes_other_station_success(
        self,
        auth_client,
        branch_manager,
        station,
        branch,
        other_station,
        other_station_branch,
        station_transaction_factory,
    ):
        own_station_tx = station_transaction_factory(station=station, station_branch=branch)
        other_station_tx = station_transaction_factory(
            station=other_station, station_branch=other_station_branch
        )

        response = auth_client(branch_manager, station_id=station.id).get(
            station_transaction_list_url()
        )

        ids = returned_ids(response)
        assert own_station_tx.id in ids
        assert other_station_tx.id not in ids

    def test_list_station_worker_scoped_to_own_created_transactions_success(
        self,
        auth_client,
        station_worker,
        station,
        branch,
        admin_user,
        station_transaction_factory,
    ):
        own_tx = station_transaction_factory(
            station=station, station_branch=branch, created_by=station_worker
        )
        admin_created_tx = station_transaction_factory(
            station=station, station_branch=branch, created_by=admin_user
        )

        response = auth_client(station_worker, station_id=station.id).get(
            station_transaction_list_url()
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert admin_created_tx.id not in ids

    def test_list_filter_by_status_success(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        approved = station_transaction_factory(
            station=station, station_branch=branch, status="approved"
        )
        pending = station_transaction_factory(
            station=station, station_branch=branch, status="pending"
        )

        response = auth_client(admin_user).get(
            station_transaction_list_url() + "?status=approved"
        )

        ids = returned_ids(response)
        assert approved.id in ids
        assert pending.id not in ids

    def test_list_filter_by_station_success(
        self,
        auth_client,
        admin_user,
        station,
        branch,
        other_station,
        other_station_branch,
        station_transaction_factory,
    ):
        own_tx = station_transaction_factory(station=station, station_branch=branch)
        other_tx = station_transaction_factory(
            station=other_station, station_branch=other_station_branch
        )

        response = auth_client(admin_user).get(
            station_transaction_list_url() + f"?station={station.id}"
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_search_by_station_name_success(
        self,
        auth_client,
        admin_user,
        station,
        branch,
        other_station,
        other_station_branch,
        station_transaction_factory,
    ):
        own_tx = station_transaction_factory(station=station, station_branch=branch)
        other_tx = station_transaction_factory(
            station=other_station, station_branch=other_station_branch
        )

        response = auth_client(admin_user).get(
            station_transaction_list_url() + f"?search={station.name}"
        )

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_empty_for_station_owner_with_no_transactions_success(
        self, auth_client, station_owner, station
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            station_transaction_list_url()
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []
