import pytest

from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import StationBranchManager, StationOwner, User, Worker


@pytest.fixture
def station(db, admin_user, geo_data):
    return Station.objects.create(
        name="Station 1",
        address="Address 1",
        lang=31.2357,
        lat=30.0444,
        district=geo_data["district"],
        created_by=admin_user,
    )

@pytest.fixture
def branch(db, admin_user, geo_data, station):
    return StationBranch.objects.create(
        name="Branch 1",
        address="Branch Address 1",
        lang=31.2357,
        lat=30.0444,
        district=geo_data["district"],
        station=station,
        created_by=admin_user,
    )

@pytest.fixture
def station_owner(db, admin_user, station):
    return StationOwner.objects.create(
        name="Station Owner 1",
        phone_number="01000000007",
        email="station_owner@example.com",
        password="password123",
        role=User.UserRoles.StationOwner,
        station=station,
        created_by=admin_user,
    )

@pytest.fixture
def branch_manager(db, admin_user, station, branch):
    manager = StationOwner.objects.create(
        name="Station Branch Manager 1",
        phone_number="01000000008",
        email="station_branch_manager@example.com",
        password="password123",
        role=User.UserRoles.StationBranchManager,
        station=station,
        created_by=admin_user,
    )
    StationBranchManager.objects.create(
        station_branch=branch, user=manager, created_by=admin_user
    )
    return manager

@pytest.fixture
def station_worker(db, admin_user, branch):
    return Worker.objects.create(
        name="Worker 1",
        phone_number="01000000009",
        email="worker@example.com",
        password="password123",
        role=User.UserRoles.StationWorker,
        station_branch=branch,
        created_by=admin_user,
    )
