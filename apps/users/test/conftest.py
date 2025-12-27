import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.geo.models import City, Country, District
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import StationBranchManager, StationOwner, User, Worker


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        name="Admin User",
        phone_number="01000000001",
        email="admin@example.com",
        password="password123",
        role=User.UserRoles.Admin,
    )


@pytest.fixture
def geo_data(db):
    country = Country.objects.create(name="Egypt", code="EG")
    city = City.objects.create(name="Cairo", country=country)
    district = District.objects.create(name="Maadi", city=city)
    return {"country": country, "city": city, "district": district}


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
        name="Owner 1",
        phone_number="01000000002",
        email="owner1@example.com",
        password="password123",
        role=User.UserRoles.StationOwner,
        station=station,
        created_by=admin_user,
    )


@pytest.fixture
def branch_manager(db, admin_user, station, branch):
    manager = StationOwner.objects.create(
        name="Manager 1",
        phone_number="01000000003",
        email="manager1@example.com",
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
        phone_number="01000000004",
        email="worker1@example.com",
        password="password123",
        role=User.UserRoles.StationWorker,
        station_branch=branch,
        created_by=admin_user,
    )


@pytest.fixture
def auth_client(api_client):
    def _auth_client(user, station_id=None):
        access_token = AccessToken.for_user(user)
        if station_id:
            access_token["station_id"] = station_id
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(access_token)}")
        return api_client

    return _auth_client
