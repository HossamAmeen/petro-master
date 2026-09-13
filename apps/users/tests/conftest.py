from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import (
    Agent,
    CompanyUser,
    FirebaseToken,
    StationOwner,
    Supervisor,
    User,
    Worker,
)


@pytest.fixture(autouse=True)
def disable_django_template_context_copy():
    """Django's test client copies template context; that copy fails on Python 3.14."""
    with patch("django.test.client.copy", side_effect=lambda value: value):
        yield


@pytest.fixture
def admin_user(db):
    return User.objects.create(
        name="Admin User",
        phone_number="01000000000",
        email="admin@example.com",
        password="password123",
        role=User.UserRoles.Admin,
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def finance_user(db, admin_user):
    return User.objects.create(
        name="Finance User",
        phone_number="01000000001",
        email="finance@example.com",
        password="password123",
        role=User.UserRoles.Finance,
        created_by=admin_user,
    )


@pytest.fixture
def customer_support_user(db, admin_user):
    return User.objects.create(
        name="Customer Support User",
        phone_number="01000000002",
        email="support@example.com",
        password="password123",
        role=User.UserRoles.CustomerSupport,
        created_by=admin_user,
    )


@pytest.fixture
def driver_user(db, admin_user):
    return User.objects.create(
        name="Driver User",
        phone_number="01000000003",
        email="driver_user@example.com",
        password="password123",
        role=User.UserRoles.Driver,
        created_by=admin_user,
    )


@pytest.fixture
def supervisor(db, admin_user, geo_data):
    sup = Supervisor.objects.create(
        name="Supervisor User",
        phone_number="01000000004",
        email="supervisor@example.com",
        password="password123",
        created_by=admin_user,
    )
    sup.district.add(geo_data["district"])
    return sup


@pytest.fixture
def agent(db, admin_user, supervisor, geo_data):
    ag = Agent.objects.create(
        name="Agent User",
        phone_number="01000000009",
        email="agent@example.com",
        password="password123",
        team_head=supervisor,
        created_by=admin_user,
    )
    ag.district.add(geo_data["district"])
    return ag


@pytest.fixture
def other_station(db, admin_user, geo_data):
    return Station.objects.create(
        name="Station 2",
        address="Address 2",
        lang=31.2,
        lat=30.1,
        district=geo_data["district"],
        created_by=admin_user,
    )


@pytest.fixture
def other_station_branch(db, admin_user, geo_data, other_station):
    return StationBranch.objects.create(
        name="Station 2 Branch 1",
        address="Branch Address 2",
        lang=31.2,
        lat=30.1,
        district=geo_data["district"],
        station=other_station,
        created_by=admin_user,
    )


@pytest.fixture
def other_company_owner(db, admin_user, other_company):
    return CompanyUser.objects.create(
        name="Other Company Owner",
        phone_number="01600000001",
        email="other_company_owner@example.com",
        password="password123",
        role=User.UserRoles.CompanyOwner,
        company=other_company,
        created_by=admin_user,
    )


@pytest.fixture
def other_company_branch_manager(db, admin_user, other_company, other_company_branch):
    from apps.users.models import CompanyBranchManager

    manager = CompanyUser.objects.create(
        name="Other Company Branch Manager",
        phone_number="01600000002",
        email="other_company_branch_manager@example.com",
        password="password123",
        role=User.UserRoles.CompanyBranchManager,
        company=other_company,
        created_by=admin_user,
    )
    CompanyBranchManager.objects.create(
        company_branch=other_company_branch,
        user=manager,
        created_by=admin_user,
    )
    return manager


@pytest.fixture
def other_station_owner(db, admin_user, other_station):
    return StationOwner.objects.create(
        name="Other Station Owner",
        phone_number="01600000003",
        email="other_station_owner@example.com",
        password="password123",
        role=User.UserRoles.StationOwner,
        station=other_station,
        created_by=admin_user,
    )


@pytest.fixture
def other_station_worker(db, admin_user, other_station_branch):
    return Worker.objects.create(
        name="Other Worker",
        phone_number="01600000004",
        email="other_worker@example.com",
        password="password123",
        role=User.UserRoles.StationWorker,
        station_branch=other_station_branch,
        created_by=admin_user,
    )


@pytest.fixture
def inactive_finance_user(db, admin_user):
    return User.objects.create(
        name="Inactive Finance",
        phone_number="01600000005",
        email="inactive_finance@example.com",
        password="password123",
        role=User.UserRoles.Finance,
        is_active=False,
        created_by=admin_user,
    )


@pytest.fixture
def firebase_token_factory(db):
    counter = {"n": 0}

    def create_token(user, **overrides):
        counter["n"] += 1
        defaults = {
            "user": user,
            "token": f"fcm-token-{counter['n']}-{uuid4().hex[:12]}",
        }
        defaults.update(overrides)
        return FirebaseToken.objects.create(**defaults)

    return create_token


@pytest.fixture
def dashboard_user_payload_factory():
    counter = {"n": 0}

    def build(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"Dashboard User {counter['n']}",
            "phone_number": f"0161{token[:7]}",
            "email": f"dash-{token[:10]}@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "role": User.UserRoles.Finance,
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def company_owner_payload_factory(company):
    counter = {"n": 0}

    def build(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Company Owner {counter['n']}",
            "phone_number": f"0162{token[:7]}",
            "email": f"owner-{token[:10]}@example.com",
            "password": "password123",
            "company_id": company.id,
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def company_branch_manager_payload_factory(company, company_branch):
    counter = {"n": 0}

    def build(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Branch Manager {counter['n']}",
            "phone_number": f"0163{token[:7]}",
            "email": f"cmanager-{token[:10]}@example.com",
            "password": "password123",
            "company_id": company.id,
            "company_branches": [company_branch.id],
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def station_owner_payload_factory(station):
    counter = {"n": 0}

    def build(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Station Owner {counter['n']}",
            "phone_number": f"0164{token[:7]}",
            "email": f"sowner-{token[:10]}@example.com",
            "password": "password123",
            "role": User.UserRoles.StationOwner,
            "station": station.id,
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def station_branch_manager_payload_factory(station, branch):
    counter = {"n": 0}

    def build(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Station Manager {counter['n']}",
            "phone_number": f"0165{token[:7]}",
            "email": f"smanager-{token[:10]}@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "station_id": station.id,
            "station_branches": [branch.id],
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def worker_payload_factory(branch):
    counter = {"n": 0}

    def build(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Worker {counter['n']}",
            "phone_number": f"0166{token[:7]}",
            "email": f"worker-{token[:10]}@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "station_branch": branch.id,
        }
        payload.update(overrides)
        return payload

    return build


@pytest.fixture
def supervisor_payload_factory(geo_data):
    counter = {"n": 0}

    def build(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Supervisor {counter['n']}",
            "phone_number": f"0167{token[:7]}",
            "email": f"supervisor-{token[:10]}@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "district": [geo_data["district"].id],
            "credit_limit": "100.00",
        }
        payload.update(overrides)
        return payload

    return build
