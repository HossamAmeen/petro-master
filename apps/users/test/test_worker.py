import pytest
from django.urls import reverse

from apps.users.models import User, Worker


@pytest.mark.django_db
class TestWorkerViewSet:
    def test_admin_can_list_all_workers(
        self, auth_client, admin_user, station_worker, branch
    ):
        # Create another worker in another station to verify admin sees all
        worker2 = Worker.objects.create(
            name="Worker 2",
            phone_number="01000000005",
            email="w2@ex.com",
            password="pwd",
            role=User.UserRoles.StationWorker,
            station_branch=branch,
            created_by=admin_user,
        )

        client = auth_client(admin_user)
        url = reverse("workers-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        worker_ids = [w["id"] for w in data["results"]]
        assert station_worker.id in worker_ids
        assert worker2.id in worker_ids

    def test_station_owner_can_only_list_their_workers(
        self, auth_client, station_owner, station, station_worker, geo_data, admin_user
    ):
        # Create another worker in another station
        station2 = station.__class__.objects.create(
            name="Station 2",
            address="Addr 2",
            lang=0,
            lat=0,
            district=geo_data["district"],
            created_by=admin_user,
        )
        branch2 = station_worker.station_branch.__class__.objects.create(
            name="Branch 2",
            address="Addr 2",
            lang=0,
            lat=0,
            district=geo_data["district"],
            station=station2,
            created_by=admin_user,
        )
        worker2 = Worker.objects.create(
            name="Worker 2",
            phone_number="01000000005",
            email="w2@ex.com",
            password="pwd",
            role=User.UserRoles.StationWorker,
            station_branch=branch2,
            created_by=admin_user,
        )

        client = auth_client(station_owner, station.id)
        url = reverse("workers-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        worker_ids = [w["id"] for w in data["results"]]
        assert station_worker.id in worker_ids
        assert worker2.id not in worker_ids

    def test_branch_manager_can_only_list_their_workers(
        self,
        auth_client,
        branch_manager,
        station,
        branch,
        station_worker,
        geo_data,
        admin_user,
    ):
        # Create another worker in another branch of the same station
        branch2 = branch.__class__.objects.create(
            name="Branch 2",
            address="Addr 2",
            lang=0,
            lat=0,
            district=geo_data["district"],
            station=station,
            created_by=admin_user,
        )
        worker2 = Worker.objects.create(
            name="Worker 2",
            phone_number="01000000005",
            email="w2@ex.com",
            password="pwd",
            role=User.UserRoles.StationWorker,
            station_branch=branch2,
            created_by=admin_user,
        )

        client = auth_client(branch_manager, station.id)
        url = reverse("workers-list")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        worker_ids = [w["id"] for w in data["results"]]
        assert station_worker.id in worker_ids
        assert worker2.id not in worker_ids

    def test_worker_can_list_workers(self, auth_client, station_worker, station):
        client = auth_client(station_worker, station.id)
        url = reverse("workers-list")
        response = client.get(url)
        assert response.status_code == 200

    def test_unauthorized_role_denied_access(self, auth_client, admin_user):
        driver = User.objects.create(
            name="Driver User",
            phone_number="01000000006",
            email="driver@ex.com",
            password="pwd",
            role=User.UserRoles.Driver,
            created_by=admin_user,
        )
        client = auth_client(driver)
        url = reverse("workers-list")
        response = client.get(url)
        assert response.status_code == 403

    def test_create_worker_as_station_owner(
        self, auth_client, station_owner, station, branch
    ):
        client = auth_client(station_owner, station.id)
        url = reverse("workers-list")
        data = {
            "name": "New Worker",
            "phone_number": "01000000007",
            "email": "newworker@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "station_branch": branch.id,
        }
        response = client.post(url, data=data, format="json")
        assert response.status_code == 201
        assert Worker.objects.filter(email="newworker@example.com").exists()

    def test_update_worker_as_station_owner(
        self, auth_client, station_owner, station, station_worker
    ):
        client = auth_client(station_owner, station.id)
        url = reverse("workers-detail", args=[station_worker.id])
        data = {"name": "Updated Worker Name"}
        response = client.patch(url, data=data, format="json")
        assert response.status_code == 200
        station_worker.refresh_from_db()
        assert station_worker.name == "Updated Worker Name"
