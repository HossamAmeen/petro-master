import pytest
from rest_framework import status

from apps.users.models import User, Worker
from apps.users.tests.helpers import workers_list_url


pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestWorkerCreate:


    def test_create_without_authentication_fail(self, api_client, worker_payload_factory):
        response = api_client.post(
            workers_list_url(),
            worker_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Worker.objects.count() == 0


    def test_create_as_company_owner_fail(self,
        auth_client, company_owner, company, worker_payload_factory
    ):
        before = Worker.objects.count()

        response = auth_client(company_owner, company_id=company.id).post(
            workers_list_url(),
            worker_payload_factory(),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Worker.objects.count() == before


    def test_create_as_station_owner_success(self,
        auth_client, station_owner, station, branch, worker_payload_factory
    ):
        payload = worker_payload_factory()

        response = auth_client(station_owner, station_id=station.id).post(
            workers_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = Worker.objects.get(phone_number=payload["phone_number"])
        assert created.name == payload["name"]
        assert created.station_branch_id == branch.id
        assert created.role == User.UserRoles.StationWorker
        assert created.check_password("password123")
        assert created.email == payload["email"]


    def test_create_as_dashboard_success(self,
        auth_client, admin_user, branch, worker_payload_factory
    ):
        payload = worker_payload_factory()
        payload.pop("email")

        response = auth_client(admin_user).post(
            workers_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = Worker.objects.get(phone_number=payload["phone_number"])
        assert created.email == f"{payload['phone_number']}@petro.com"


    def test_create_station_admin_foreign_branch_fail(self,
        auth_client,
        station_owner,
        station,
        other_station_branch,
        worker_payload_factory,
    ):
        payload = worker_payload_factory(station_branch=other_station_branch.id)
        before = Worker.objects.count()

        response = auth_client(station_owner, station_id=station.id).post(
            workers_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Worker.objects.count() == before


    def test_create_duplicate_phone_fail(self,
        auth_client, admin_user, station_worker, worker_payload_factory
    ):
        payload = worker_payload_factory(phone_number=station_worker.phone_number)

        response = auth_client(admin_user).post(
            workers_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


    def test_create_password_mismatch_fail(self,
        auth_client, admin_user, worker_payload_factory
    ):
        payload = worker_payload_factory(confirm_password="other-pass")
        before = Worker.objects.count()

        response = auth_client(admin_user).post(
            workers_list_url(),
            payload,
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Worker.objects.count() == before
