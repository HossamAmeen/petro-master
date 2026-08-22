import pytest
from apps.stations.models.stations_models import Station, StationBranch
from apps.users.models import StationOwner, StationBranchManager, Worker, User

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
def car(db, company_branch, service):
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
    )

@pytest.fixture
def driver(db, company_branch):
    from apps.companies.models.company_models import Driver
    import datetime
    return Driver.objects.create(
        name="Test Driver",
        phone_number="01234567890",
        code="D-123",
        lincense_number="L-123",
        lincense_expiration_date=datetime.date(2030, 1, 1),
        branch=company_branch,
    )

@pytest.fixture
def gas_operation(db, car, driver, branch, station_worker, service):
    from apps.companies.models.operation_model import CarOperation
    return CarOperation.objects.create(
        car=car,
        driver=driver,
        station_branch=branch,
        worker=station_worker,
        service=service,
        status=CarOperation.OperationStatus.PENDING,
    )

@pytest.fixture
def other_operation(db, car, driver, branch, station_worker):
    from apps.companies.models.operation_model import CarOperation
    return CarOperation.objects.create(
        car=car,
        driver=driver,
        station_branch=branch,
        worker=station_worker,
        status=CarOperation.OperationStatus.PENDING,
    )
