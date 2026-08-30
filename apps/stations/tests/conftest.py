from uuid import uuid4

import pytest

from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import (
    Station,
    StationBranch,
    StationBranchService,
)
from apps.users.models import CompanyUser, StationBranchManager, StationOwner, User, Worker

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

@pytest.fixture
def service(db, admin_user):
    from apps.stations.models.service_models import Service
    return Service.objects.create(
        name="Gasoline 92",
        unit=Service.ServiceUnit.LITRE,
        type=Service.ServiceType.PETROL,
        cost=10.00,
        created_by=admin_user,
    )

@pytest.fixture
def other_service(db, admin_user):
    from apps.stations.models.service_models import Service
    return Service.objects.create(
        name="Car Wash",
        unit=Service.ServiceUnit.UNIT,
        type=Service.ServiceType.WASH,
        cost=50.00,
        created_by=admin_user,
    )

@pytest.fixture
def car(db, admin_user, company_branch, service):
    from apps.companies.models.company_models import Car
    return Car.objects.create(
        code="C-123",
        plate_number="1234",
        plate_character="ABC",
        plate_color=Car.PlateColor.RED,
        color="Black",
        model_year=2022,
        brand="Toyota",
        is_with_odometer=True,
        tank_capacity=50,
        permitted_fuel_amount=50,
        fuel_type=Car.FuelType.GASOLINE,
        number_of_fuelings_per_day=1,
        number_of_washes_per_month=1,
        balance=1000.00,
        branch=company_branch,
        service=service,
        last_meter=10000,
        created_by=admin_user,
    )

@pytest.fixture
def driver(db, admin_user, company_branch):
    from apps.companies.models.company_models import Driver
    import datetime
    return Driver.objects.create(
        name="Test Driver",
        phone_number="01234567890",
        code="D-123",
        lincense_number="L-123",
        lincense_expiration_date=datetime.date(2030, 1, 1),
        branch=company_branch,
        created_by=admin_user,
    )

@pytest.fixture
def gas_operation(db, admin_user, car, driver, branch, station_worker, service):
    from apps.companies.models.operation_model import CarOperation
    return CarOperation.objects.create(
        car=car,
        driver=driver,
        station_branch=branch,
        worker=station_worker,
        service=service,
        status=CarOperation.OperationStatus.PENDING,
        created_by=admin_user,
    )

@pytest.fixture
def other_operation(db, admin_user, car, driver, branch, station_worker):
    from apps.companies.models.operation_model import CarOperation
    return CarOperation.objects.create(
        car=car,
        driver=driver,
        station_branch=branch,
        worker=station_worker,
        status=CarOperation.OperationStatus.PENDING,
        created_by=admin_user,
    )


@pytest.fixture
def station_factory(db, admin_user, geo_data):
    counter = {"n": 0}

    def create_station(**overrides):
        counter["n"] += 1
        defaults = {
            "name": f"Factory Station {counter['n']}",
            "address": f"Factory Station Address {counter['n']}",
            "lang": 31.2357,
            "lat": 30.0444,
            "district": geo_data["district"],
            "balance": 0,
            "created_by": admin_user,
        }
        defaults.update(overrides)
        return Station.objects.create(**defaults)

    return create_station


@pytest.fixture
def station_branch_factory(db, admin_user, geo_data, station):
    counter = {"n": 0}

    def create_branch(**overrides):
        counter["n"] += 1
        defaults = {
            "name": f"Factory Station Branch {counter['n']}",
            "address": f"Factory Branch Address {counter['n']}",
            "lang": 31.2357,
            "lat": 30.0444,
            "district": geo_data["district"],
            "station": station,
            "created_by": admin_user,
        }
        defaults.update(overrides)
        return StationBranch.objects.create(**defaults)

    return create_branch


@pytest.fixture
def station_payload_factory(geo_data):
    counter = {"n": 0}

    def build_payload(**overrides):
        counter["n"] += 1
        payload = {
            "name": f"New Station {counter['n']}",
            "address": f"New Station Address {counter['n']}",
            "lang": 31.2357,
            "lat": 30.0444,
            "district": geo_data["district"].id,
        }
        payload.update(overrides)
        return payload

    return build_payload


@pytest.fixture
def station_branch_payload_factory(station, geo_data):
    counter = {"n": 0}

    def build_payload(**overrides):
        counter["n"] += 1
        payload = {
            "name": f"New Station Branch {counter['n']}",
            "address": f"New Branch Address {counter['n']}",
            "lang": 31.2357,
            "lat": 30.0444,
            "district": geo_data["district"].id,
            "station": station.id,
            "fees": "0.00",
            "other_service_fees": "0.00",
            "cash_request_fees": "0.00",
        }
        payload.update(overrides)
        return payload

    return build_payload


@pytest.fixture
def other_station(station_factory):
    return station_factory(name="Other Station")


@pytest.fixture
def other_station_branch(station_branch_factory, other_station):
    return station_branch_factory(
        name="Other Station Branch",
        station=other_station,
    )


@pytest.fixture
def other_station_owner(db, admin_user, other_station):
    token = uuid4().hex[:8]
    return StationOwner.objects.create(
        name="Other Station Owner",
        phone_number=f"012{token[:8]}",
        email=f"other-station-owner-{token}@example.com",
        password="password123",
        role=User.UserRoles.StationOwner,
        station=other_station,
        created_by=admin_user,
    )


@pytest.fixture
def other_company_owner(db, admin_user, other_company):
    token = uuid4().hex[:8]
    return CompanyUser.objects.create(
        name="Other Company Owner",
        phone_number=f"014{token[:8]}",
        email=f"other-company-owner-{token}@example.com",
        password="password123",
        role=User.UserRoles.CompanyOwner,
        company=other_company,
        created_by=admin_user,
    )


@pytest.fixture
def second_station_branch(station_branch_factory):
    return station_branch_factory(name="Station Branch 2")


@pytest.fixture
def second_station_worker(db, admin_user, second_station_branch):
    token = uuid4().hex[:8]
    return Worker.objects.create(
        name="Worker 2",
        phone_number=f"015{token[:8]}",
        email=f"worker-2-{token}@example.com",
        password="password123",
        role=User.UserRoles.StationWorker,
        station_branch=second_station_branch,
        created_by=admin_user,
    )


@pytest.fixture
def second_station_owner(db, admin_user, station):
    token = uuid4().hex[:8]
    return StationOwner.objects.create(
        name="Station Owner 2",
        phone_number=f"016{token[:8]}",
        email=f"station-owner-2-{token}@example.com",
        password="password123",
        role=User.UserRoles.StationOwner,
        station=station,
        created_by=admin_user,
    )


@pytest.fixture
def diesel_service(db, admin_user):
    return Service.objects.create(
        name="Diesel 80",
        unit=Service.ServiceUnit.LITRE,
        type=Service.ServiceType.DIESEL,
        cost=12.00,
        created_by=admin_user,
    )


@pytest.fixture
def station_branch_service_factory(db, admin_user):
    def create_link(station_branch, service):
        return StationBranchService.objects.create(
            station_branch=station_branch,
            service=service,
            created_by=admin_user,
        )

    return create_link


@pytest.fixture
def branch_petrol_service(station_branch_service_factory, branch, service):
    return station_branch_service_factory(branch, service)


@pytest.fixture
def branch_other_service(station_branch_service_factory, branch, other_service):
    return station_branch_service_factory(branch, other_service)


@pytest.fixture
def second_branch_company_manager(branch_manager_user_factory, second_company_branch):
    return branch_manager_user_factory(branch=second_company_branch)
