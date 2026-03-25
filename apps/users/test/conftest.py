import pytest
from apps.users.models import User, Supervisor, Agent

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
def finance_user(db, admin_user):
    return User.objects.create(
        name="Finance User",
        phone_number="01000000002",
        email="finance@example.com",
        password="password123",
        role=User.UserRoles.Finance,
        created_by=admin_user,
    )

@pytest.fixture
def customer_support_user(db, admin_user):
    return User.objects.create(
        name="Customer Support User",
        phone_number="01000000003",
        email="support@example.com",
        password="password123",
        role=User.UserRoles.CustomerSupport,
        created_by=admin_user,
    )

@pytest.fixture
def driver_user(db, admin_user):
    return User.objects.create(
        name="Driver User",
        phone_number="01000000004",
        email="driver@example.com",
        password="password123",
        role=User.UserRoles.Driver,
        created_by=admin_user,
    )

@pytest.fixture
def supervisor(db, admin_user, geo_data):
    sup = Supervisor.objects.create(
        name="Supervisor 1",
        phone_number="01000000010",
        email="supervisor@example.com",
        password="password123",
        role=User.UserRoles.Supervisor,
        created_by=admin_user,
    )
    sup.district.add(geo_data["district"])
    return sup

@pytest.fixture
def agent(db, admin_user, geo_data, supervisor):
    ag = Agent.objects.create(
        name="Agent 1",
        phone_number="01000000011",
        email="agent@example.com",
        password="password123",
        role=User.UserRoles.Agent,
        team_head=supervisor,
        created_by=admin_user,
    )
    ag.district.add(geo_data["district"])
    return ag
