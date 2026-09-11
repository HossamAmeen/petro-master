"""The dashboard onboards a station; its owner staffs it and the staff log in."""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.auth.tests.helpers import decode_access
from apps.stations.models.stations_models import Station, StationBranch
from apps.stations.tests.helpers import home_url
from apps.users.models import StationOwner, User, Worker

from .helpers import login, login_client, sign_in, station_branch_action_url

pytestmark = [pytest.mark.django_db, pytest.mark.feature]

PASSWORD = "password123"


def service_ids(response):
    return {item["id"] for item in response.data["results"]}


def staff_payload(phone_number, **extra):
    return {
        "name": f"Staff {phone_number}",
        "phone_number": phone_number,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        **extra,
    }


class TestStationOnboarding:
    @pytest.fixture(autouse=True)
    def setup(self, admin_user, geo_data, service, other_service):
        self.admin = sign_in("dashboard", admin_user)
        self.district = geo_data["district"]
        self.services = [service, other_service]

    def create_station(self, client, name="Delta Fuel"):
        response = client.post(
            reverse("stations-list"),
            {
                "name": name,
                "address": "Ring Road",
                "lang": 31.2,
                "lat": 30.0,
                "district": self.district.id,
            },
            format="json",
        )
        return response, Station.objects.filter(name=name).first()

    def create_branch(self, client, station, name="Delta Ring Road"):
        response = client.post(
            reverse("station-branches-list"),
            {
                "name": name,
                "address": "Ring Road km 12",
                "lang": 31.2,
                "lat": 30.0,
                "district": self.district.id,
                "station": station.id,
            },
            format="json",
        )
        return response, StationBranch.objects.filter(name=name).first()

    def test_dashboard_onboards_station_and_staff_log_in_success(self):
        station_created, station = self.create_station(self.admin)
        branch_created, branch = self.create_branch(self.admin, station)
        assigned = self.admin.post(
            station_branch_action_url("assign-services", branch.id),
            {"services": [item.id for item in self.services]},
            format="json",
        )
        manager_created = self.admin.post(
            reverse("station-branch-managers-list"),
            staff_payload(
                "01711111111", station_id=station.id, station_branches=[branch.id]
            ),
            format="json",
        )
        worker_created = self.admin.post(
            reverse("workers-list"),
            staff_payload("01722222222", station_branch=branch.id),
            format="json",
        )
        manager = StationOwner.objects.get(phone_number="01711111111")
        worker = Worker.objects.get(phone_number="01722222222")

        worker_login = login("station", worker)
        manager_login = login("station", manager)

        assert station_created.status_code == status.HTTP_201_CREATED
        assert branch_created.status_code == status.HTTP_201_CREATED
        assert assigned.status_code == status.HTTP_200_OK, assigned.data
        assert manager_created.status_code == status.HTTP_201_CREATED
        assert worker_created.status_code == status.HTTP_201_CREATED
        assert manager.role == User.UserRoles.StationBranchManager
        assert worker_login.status_code == status.HTTP_200_OK, worker_login.data
        assert decode_access(worker_login.data["access"])["station_id"] == station.id
        assert manager_login.status_code == status.HTTP_200_OK, manager_login.data
        assert manager_login.data["station_id"] == station.id

        worker_home = login_client("station", worker).get(home_url())
        manager_client = login_client("station", manager)
        manager_home = manager_client.get(home_url())
        branch_services = manager_client.get(
            station_branch_action_url("services", branch.id)
        )

        assert worker_home.data["station_branch_id"] == branch.id
        assert manager_home.data["branches_count"] == 1
        assert manager_home.data["workers_count"] == 1
        assert service_ids(branch_services) == {item.id for item in self.services}

    def test_api_created_station_owner_cannot_log_in_fail(self):
        """Open issue: `StationOwnerSerializer` is a plain `fields="__all__"`
        ModelSerializer and never hashes, so the password is stored as typed."""
        _, station = self.create_station(self.admin)

        created = self.admin.post(
            reverse("station-owners-list"),
            {
                "name": "Delta Owner",
                "phone_number": "01733333333",
                "email": "delta-owner@example.com",
                "password": PASSWORD,
                "role": User.UserRoles.StationOwner,
                "station": station.id,
            },
            format="json",
        )
        owner = StationOwner.objects.get(phone_number="01733333333")

        response = login("station", owner)

        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert owner.password == PASSWORD
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_owner_staffs_their_own_station_success(
        self, station, branch, station_owner
    ):
        owner = sign_in("station", station_owner)

        worker_created = owner.post(
            reverse("workers-list"),
            staff_payload("01744444444", station_branch=branch.id),
            format="json",
        )
        manager_created = owner.post(
            reverse("station-branch-managers-list"),
            staff_payload("01755555555"),
            format="json",
        )
        manager = StationOwner.objects.get(phone_number="01755555555")
        assigned = owner.post(
            station_branch_action_url("assign-managers", branch.id),
            {"managers": [manager.id]},
            format="json",
        )
        added = owner.post(
            station_branch_action_url("add-service", branch.id),
            {"services": [self.services[0].id]},
            format="json",
        )
        home = owner.get(home_url())

        assert (
            worker_created.status_code == status.HTTP_201_CREATED
        ), worker_created.data
        assert manager_created.status_code == status.HTTP_201_CREATED
        assert manager.station_id == station.id
        assert assigned.status_code == status.HTTP_200_OK, assigned.data
        assert added.status_code == status.HTTP_200_OK, added.data
        assert home.data["workers_count"] == 1
        assert home.data["managers_count"] == 1
        assert home.data["branches_count"] == 1
        assert login("station", manager).status_code == status.HTTP_200_OK

    def test_owner_cannot_staff_another_station_fail(
        self, station_owner, other_station_branch
    ):
        owner = sign_in("station", station_owner)

        response = owner.post(
            reverse("workers-list"),
            staff_payload("01766666666", station_branch=other_station_branch.id),
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Worker.objects.filter(phone_number="01766666666").exists()

    def test_station_roles_cannot_create_stations_or_branches_fail(
        self, station, station_owner
    ):
        owner = sign_in("station", station_owner)

        station_response, _ = self.create_station(owner, "Owner Station")
        branch_response, _ = self.create_branch(owner, station, "Owner Branch")

        assert station_response.status_code == status.HTTP_403_FORBIDDEN
        assert branch_response.status_code == status.HTTP_403_FORBIDDEN
        assert not StationBranch.objects.filter(name="Owner Branch").exists()
