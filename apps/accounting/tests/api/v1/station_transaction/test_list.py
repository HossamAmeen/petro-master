import pytest
from rest_framework import status

from apps.users.tests.helpers import user_ref

from .helpers import station_transaction_list_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def returned_ids(response):
    return {row["id"] for row in response.data["results"]}


class TestStationKhaznaTransactionList:
    @pytest.fixture(autouse=True)
    def setup(
        self, auth_client, admin_user, station, branch, station_transaction_factory
    ):
        self.auth_client = auth_client
        self.admin = admin_user
        self.admin_client = auth_client(admin_user)
        self.station = station
        self.branch = branch
        self.create_transaction = station_transaction_factory
        self.url = station_transaction_list_url()

    def list(self, client=None, query=""):
        return (client or self.admin_client).get(self.url + query)

    def station_client(self, user):
        return self.auth_client(user, station_id=self.station.id)

    def test_list_unauthenticated_fail(self, api_client):
        response = self.list(client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_company_role_forbidden_fail(self, company_owner, company):
        client = self.auth_client(company_owner, company_id=company.id)

        response = self.list(client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_dashboard_user_success(self):
        tx = self.create_transaction()

        response = self.list()

        assert response.status_code == status.HTTP_200_OK
        assert tx.id in returned_ids(response)

    def test_list_serializer_shape_success(self):
        tx = self.create_transaction()

        response = self.list()

        item = next(row for row in response.data["results"] if row["id"] == tx.id)
        assert item["station"] == {"id": self.station.id, "name": self.station.name}
        assert item["station_branch"]["id"] == self.branch.id
        assert item["station_branch"]["name"] == self.branch.name

    def test_list_station_owner_scoped_to_own_station_success(
        self, station_owner, other_station, other_station_branch
    ):
        own_tx = self.create_transaction()
        other_tx = self.create_transaction(
            station=other_station, station_branch=other_station_branch
        )

        response = self.list(client=self.station_client(station_owner))

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_station_branch_manager_sees_whole_station_not_just_managed_branch_success(
        self, branch_manager, second_station_branch
    ):
        """Documents actual behavior: the queryset filter
        `station__branches__managers__user` matches on the *station* having
        any branch managed by this user, not on the specific managed branch.
        So a branch manager sees every transaction for the whole station,
        including branches they do not manage (unlike
        `CompanyBranchManager`, which is scoped per-branch)."""
        managed_branch_tx = self.create_transaction()
        other_branch_tx = self.create_transaction(station_branch=second_station_branch)

        response = self.list(client=self.station_client(branch_manager))

        ids = returned_ids(response)
        assert managed_branch_tx.id in ids
        assert other_branch_tx.id in ids

    def test_list_station_branch_manager_excludes_other_station_success(
        self, branch_manager, other_station, other_station_branch
    ):
        own_station_tx = self.create_transaction()
        other_station_tx = self.create_transaction(
            station=other_station, station_branch=other_station_branch
        )

        response = self.list(client=self.station_client(branch_manager))

        ids = returned_ids(response)
        assert own_station_tx.id in ids
        assert other_station_tx.id not in ids

    def test_list_station_worker_scoped_to_own_created_transactions_success(
        self, station_worker
    ):
        own_tx = self.create_transaction(created_by=station_worker)
        admin_created_tx = self.create_transaction(created_by=self.admin)

        response = self.list(client=self.station_client(station_worker))

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert admin_created_tx.id not in ids

    def test_list_filter_by_status_success(self):
        approved = self.create_transaction(status="approved")
        pending = self.create_transaction(status="pending")

        response = self.list(query="?status=approved")

        ids = returned_ids(response)
        assert approved.id in ids
        assert pending.id not in ids

    def test_list_filter_by_station_success(self, other_station, other_station_branch):
        own_tx = self.create_transaction()
        other_tx = self.create_transaction(
            station=other_station, station_branch=other_station_branch
        )

        response = self.list(query=f"?station={self.station.id}")

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_search_by_station_name_success(
        self, other_station, other_station_branch
    ):
        own_tx = self.create_transaction()
        other_tx = self.create_transaction(
            station=other_station, station_branch=other_station_branch
        )

        response = self.list(query=f"?search={self.station.name}")

        ids = returned_ids(response)
        assert own_tx.id in ids
        assert other_tx.id not in ids

    def test_list_empty_for_station_owner_with_no_transactions_success(
        self, station_owner
    ):
        response = self.list(client=self.station_client(station_owner))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["results"] == []

    def test_list_includes_created_by_and_updated_by_success(self, finance_user):
        edited_tx = self.create_transaction(
            created_by=self.admin, updated_by=finance_user
        )
        new_tx = self.create_transaction(created_by=finance_user, updated_by=None)

        response = self.list()

        assert response.status_code == status.HTTP_200_OK
        rows = {row["id"]: row for row in response.data["results"]}
        assert rows[edited_tx.id]["created_by"] == user_ref(self.admin)
        assert rows[edited_tx.id]["updated_by"] == user_ref(finance_user)
        assert rows[new_tx.id]["created_by"] == user_ref(finance_user)
        assert rows[new_tx.id]["updated_by"] is None

    @pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
    def test_list_other_dashboard_roles_success(self, role_fixture, request):
        tx = self.create_transaction()
        client = self.auth_client(request.getfixturevalue(role_fixture))

        response = self.list(client=client)

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {tx.id}
