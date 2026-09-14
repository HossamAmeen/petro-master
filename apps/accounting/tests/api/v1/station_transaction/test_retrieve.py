import pytest
from rest_framework import status

from .helpers import station_transaction_detail_url

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationKhaznaTransactionRetrieve:
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

    def retrieve(self, pk, client=None):
        return (client or self.admin_client).get(station_transaction_detail_url(pk))

    def station_client(self, user):
        return self.auth_client(user, station_id=self.station.id)

    def test_retrieve_unauthenticated_fail(self, api_client):
        tx = self.create_transaction()

        response = self.retrieve(tx.id, client=api_client)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_not_found_fail(self):
        response = self.retrieve(999999)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_company_role_forbidden_fail(self, company_owner, company):
        tx = self.create_transaction()
        client = self.auth_client(company_owner, company_id=company.id)

        response = self.retrieve(tx.id, client=client)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_dashboard_user_success(self):
        tx = self.create_transaction()

        response = self.retrieve(tx.id)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
        assert response.data["station"] == {
            "id": self.station.id,
            "name": self.station.name,
        }
        assert response.data["station_branch"]["id"] == self.branch.id
        assert response.data["reference_code"] == tx.reference_code

    def test_retrieve_station_owner_success(self, station_owner):
        tx = self.create_transaction()

        response = self.retrieve(tx.id, client=self.station_client(station_owner))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id

    def test_retrieve_station_owner_cannot_see_other_station_transaction_fail(
        self, station_owner, other_station, other_station_branch
    ):
        tx = self.create_transaction(
            station=other_station, station_branch=other_station_branch
        )

        response = self.retrieve(tx.id, client=self.station_client(station_owner))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_station_worker_cannot_see_transaction_created_by_another_user_fail(
        self, station_worker
    ):
        tx = self.create_transaction(created_by=self.admin)

        response = self.retrieve(tx.id, client=self.station_client(station_worker))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_station_worker_own_transaction_success(self, station_worker):
        tx = self.create_transaction(created_by=station_worker)

        response = self.retrieve(tx.id, client=self.station_client(station_worker))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == tx.id
