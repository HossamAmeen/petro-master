import pytest
from rest_framework import status

from apps.users.models import Worker
from apps.users.tests.helpers import workers_detail_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestWorkerRetrieve:


    def test_retrieve_without_authentication_fail(self, api_client, station_worker):
        response = api_client.get(workers_detail_url(station_worker.id))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


    def test_retrieve_as_company_owner_fail(self,
        auth_client, company_owner, company, station_worker
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            workers_detail_url(station_worker.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


    def test_retrieve_success(self, auth_client, admin_user, station_worker, branch, station):
        response = auth_client(admin_user).get(workers_detail_url(station_worker.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == station_worker.id
        assert response.data["name"] == station_worker.name
        assert response.data["phone_number"] == station_worker.phone_number
        assert response.data["station_branch"]["id"] == branch.id
        assert response.data["station_branch"]["station"] == station.id


    def test_retrieve_other_station_as_owner_fail(self,
        auth_client, station_owner, station, other_station_worker
    ):
        response = auth_client(station_owner, station_id=station.id).get(
            workers_detail_url(other_station_worker.id)
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


    def test_update_name_success(self, auth_client, station_owner, station, station_worker):
        response = auth_client(station_owner, station_id=station.id).patch(
            workers_detail_url(station_worker.id),
            {"name": "Updated Worker"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        station_worker.refresh_from_db()
        assert station_worker.name == "Updated Worker"


    def test_update_password_success(self, auth_client, admin_user, station_worker):
        response = auth_client(admin_user).patch(
            workers_detail_url(station_worker.id),
            {"password": "new-worker-pass", "confirm_password": "new-worker-pass"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        station_worker.refresh_from_db()
        assert station_worker.check_password("new-worker-pass")


    def test_update_password_without_confirm_fail(self, auth_client, admin_user, station_worker):
        response = auth_client(admin_user).patch(
            workers_detail_url(station_worker.id),
            {"password": "new-worker-pass"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


    def test_update_password_mismatch_fail(self, auth_client, admin_user, station_worker):
        response = auth_client(admin_user).patch(
            workers_detail_url(station_worker.id),
            {"password": "new-worker-pass", "confirm_password": "other-pass"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


    def test_delete_as_company_owner_fail(self,
        auth_client, company_owner, company, station_worker
    ):
        response = auth_client(company_owner, company_id=company.id).delete(
            workers_detail_url(station_worker.id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Worker.objects.filter(pk=station_worker.id).exists()


    def test_delete_success(self, auth_client, admin_user, other_station_worker):
        user_id = other_station_worker.id

        response = auth_client(admin_user).delete(workers_detail_url(user_id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Worker.objects.filter(pk=user_id).exists()
