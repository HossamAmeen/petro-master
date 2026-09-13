from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.factories import (
    CarCodeFactory,
    CarFactory,
    CarOperationFactory,
    CompanyBranchFactory,
    CompanyCashRequestFactory,
    CompanyFactory,
    CompanyKhaznaTransactionFactory,
    DriverFactory,
)
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Car, Company, CompanyBranch
from apps.companies.models.operation_model import CarOperation
from apps.geo.models import City, District
from apps.stations.models.service_models import Service
from apps.users.models import CompanyBranchManager, CompanyUser, User


@pytest.fixture
def company_factory(db, admin_user, geo_data):
    counter = {"n": 0}

    def create_company(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        defaults = {
            "name": f"Factory Company {counter['n']}",
            "address": f"Factory Address {counter['n']}",
            "email": f"factory-company-{token[:10]}@example.com",
            "phone_number": f"015{token[:8]}",
            "district": geo_data["district"],
            "is_active": True,
            "balance": Decimal("0.00"),
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        return CompanyFactory(**defaults)

    return create_company


@pytest.fixture
def company_payload_factory(geo_data):
    counter = {"n": 0}

    def build_company_payload(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Company {counter['n']}",
            "email": f"new-company-{token[:10]}@example.com",
            "phone_number": f"016{token[:8]}",
            "address": f"New Company Address {counter['n']}",
            "district": geo_data["district"].id,
            "is_active": True,
        }
        payload.update(overrides)
        return payload

    return build_company_payload


@pytest.fixture
def company(db, admin_user, geo_data):
    return Company.objects.create(
        name="Company 1",
        address="Company Address 1",
        district=geo_data["district"],
        created_by=admin_user,
    )


@pytest.fixture
def company_owner(db, admin_user, company):
    return CompanyUser.objects.create(
        name="Company Owner 1",
        phone_number="01000000005",
        email="company_owner@example.com",
        password="password123",
        role=User.UserRoles.CompanyOwner,
        company=company,
        created_by=admin_user,
    )


@pytest.fixture
def company_branch(db, admin_user, company, geo_data):
    return CompanyBranch.objects.create(
        name="Company Branch 1",
        company=company,
        district=geo_data["district"],
        created_by=admin_user,
    )


@pytest.fixture
def company_branch_factory(db, admin_user, company, geo_data):
    counter = {"n": 0}

    def create_branch(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        defaults = {
            "name": f"Factory Branch {counter['n']}",
            "email": f"branch-{token[:8]}@example.com",
            "phone_number": f"018{token[:8]}",
            "address": f"Branch Address {counter['n']}",
            "company": company,
            "district": geo_data["district"],
            "balance": Decimal("0.00"),
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        return CompanyBranchFactory(**defaults)

    return create_branch


@pytest.fixture
def company_branch_payload_factory(company, geo_data):
    counter = {"n": 0}

    def build_branch_payload(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Branch {counter['n']}",
            "email": f"new-branch-{token[:8]}@example.com",
            "phone_number": f"019{token[:8]}",
            "address": f"New Branch Address {counter['n']}",
            "district": geo_data["district"].id,
            "fees": "0.00",
            "other_service_fees": "0.00",
            "cash_request_fees": "0.00",
            "company": company.id,
        }
        payload.update(overrides)
        return payload

    return build_branch_payload


@pytest.fixture
def branch_manager_user_factory(db, admin_user, company):
    counter = {"n": 0}

    def create_manager(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        branch = overrides.pop("branch", None)
        defaults = {
            "name": f"Manager User {counter['n']}",
            "phone_number": f"013{token[:8]}",
            "email": f"mgr-{token[:10]}@example.com",
            "password": "password123",
            "role": User.UserRoles.CompanyBranchManager,
            "company": company,
            "created_by": admin_user,
        }
        defaults.update(overrides)
        user = CompanyUser.objects.create(**defaults)
        if branch is not None:
            CompanyBranchManager.objects.create(
                company_branch=branch,
                user=user,
                created_by=admin_user,
            )
        return user

    return create_manager


@pytest.fixture
def company_branch_manager(db, admin_user, company_branch, company):
    manager_user = CompanyUser.objects.create(
        name="Company Branch Manager 1",
        phone_number="01000000006",
        email="company_branch_manager@example.com",
        password="password123",
        role=User.UserRoles.CompanyBranchManager,
        company=company,
        created_by=admin_user,
    )
    CompanyBranchManager.objects.create(
        company_branch=company_branch,
        user=manager_user,
        created_by=admin_user,
    )
    return manager_user


@pytest.fixture
def car_code_factory(db, admin_user):
    def create_car_code(**overrides):
        return CarCodeFactory(
            created_by=admin_user,
            updated_by=admin_user,
            **overrides,
        )

    return create_car_code


@pytest.fixture
def car_factory(db, admin_user, company_branch, geo_data, service):
    def create_car(**overrides):
        defaults = {
            "branch": company_branch,
            "city": geo_data["city"],
            "service": service,
            "plate_number": "1234",
            "plate_character": "ABC",
            "plate_color": Car.PlateColor.RED,
            "color": "Black",
            "model_year": 2024,
            "brand": "Toyota",
            "is_with_odometer": True,
            "tank_capacity": 60,
            "permitted_fuel_amount": 40,
            "fuel_type": Car.FuelType.GASOLINE,
            "number_of_fuelings_per_day": 2,
            "number_of_washes_per_month": 4,
            "balance": Decimal("0.00"),
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        return CarFactory(**defaults)

    return create_car


@pytest.fixture
def company_car(car_factory):
    return car_factory()


@pytest.fixture
def car_payload_factory(company_branch, geo_data, service, car_code_factory):
    def build_car_payload(**overrides):
        car_code = overrides.pop("car_code", None) or car_code_factory()
        payload = {
            "code": car_code.code,
            "plate_number": "5678",
            "plate_character": "XYZ",
            "plate_color": Car.PlateColor.BLUE,
            "color": "White",
            "model_year": 2025,
            "brand": "Honda",
            "is_with_odometer": True,
            "tank_capacity": 70,
            "permitted_fuel_amount": 50,
            "fuel_type": Car.FuelType.GASOLINE,
            "service": service.id,
            "number_of_fuelings_per_day": 2,
            "number_of_washes_per_month": 3,
            "fuel_allowed_days": [Car.FuelAllowedDay.MON],
            "city": geo_data["city"].id,
            "branch": company_branch.id,
        }
        payload.update(overrides)
        return payload

    return build_car_payload


@pytest.fixture
def other_company(admin_user, geo_data):
    return CompanyFactory(
        name="Company 2",
        district=geo_data["district"],
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def other_company_branch(admin_user, geo_data, other_company):
    return CompanyBranchFactory(
        name="Company Branch 2",
        company=other_company,
        district=geo_data["district"],
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def second_company_branch(admin_user, company, geo_data):
    return CompanyBranchFactory(
        name="Company Branch 1B",
        company=company,
        district=geo_data["district"],
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def other_city_company_branch(admin_user, company, geo_data):
    city = City.objects.create(name="Alexandria", country=geo_data["country"])
    district = District.objects.create(name="Smouha", city=city)
    return CompanyBranchFactory(
        name="Alexandria Branch",
        company=company,
        district=district,
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.fixture
def driver_factory(db, admin_user, company_branch):
    counter = {"n": 0}

    def create_driver(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        defaults = {
            "name": f"Driver {counter['n']}",
            "phone_number": f"011{token[:8]}",
            "code": token[:10].upper(),
            "lincense_number": f"LIC{token[:17]}".upper(),
            "lincense_expiration_date": timezone.localdate() + timedelta(days=180),
            "branch": company_branch,
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        return DriverFactory(**defaults)

    return create_driver


@pytest.fixture
def company_driver(driver_factory):
    return driver_factory()


@pytest.fixture
def car_operation_factory(
    db, admin_user, branch, station_worker, company_car, company_driver, service
):
    def create_car_operation(**overrides):
        defaults = {
            "station_branch": branch,
            "worker": station_worker,
            "car": company_car,
            "driver": company_driver,
            "service": service,
            "status": CarOperation.OperationStatus.PENDING,
            "amount": Decimal("10.00"),
            "unit": Service.ServiceUnit.LITRE,
            "duration": 120,
            "cost": Decimal("100.00"),
            "company_cost": Decimal("100.00"),
            "station_cost": Decimal("100.00"),
            "profits": Decimal("0.00"),
            "fuel_type": Car.FuelType.GASOLINE,
            "car_meter": Decimal("10000.00"),
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        return CarOperationFactory(**defaults)

    return create_car_operation


@pytest.fixture
def car_operation_payload_factory(
    company_car, company_driver, branch, station_worker, service
):
    def build_payload(**overrides):
        start = timezone.now()
        payload = {
            "car": company_car.id,
            "driver": company_driver.id,
            "station_branch": branch.id,
            "worker": station_worker.id,
            "service": service.id,
            "amount": "10.00",
            "car_meter": "100.00",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(minutes=5)).isoformat(),
            "status": CarOperation.OperationStatus.PENDING,
            "fuel_type": Car.FuelType.GASOLINE,
        }
        payload.update(overrides)
        return payload

    return build_payload


@pytest.fixture
def cash_request_factory(db, admin_user):
    def create_cash_request(**overrides):
        defaults = {
            "amount": Decimal("50.00"),
            "status": CompanyCashRequest.Status.IN_PROGRESS,
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        defaults.setdefault("company_cost", defaults["amount"])
        with patch("apps.companies.helper.send_sms"):
            return CompanyCashRequestFactory(**defaults)

    return create_cash_request


@pytest.fixture
def cash_request_payload_factory(company_driver):
    def build_payload(**overrides):
        payload = {
            "driver": company_driver.id,
            "amount": "50.00",
        }
        payload.update(overrides)
        return payload

    return build_payload


@pytest.fixture
def company_transaction_factory(db, admin_user, company, company_branch):
    counter = {"n": 0}

    def create_transaction(**overrides):
        counter["n"] += 1
        defaults = {
            "company": company,
            "company_branch": company_branch,
            "amount": Decimal("10.00"),
            "status": CompanyKhaznaTransaction.TransactionStatus.APPROVED,
            "reference_code": f"HMREF{counter['n']:05d}",
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        return CompanyKhaznaTransactionFactory(**defaults)

    return create_transaction


@pytest.fixture
def driver_payload_factory(company_branch):
    counter = {"n": 0}

    def build_driver_payload(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        payload = {
            "name": f"New Driver {counter['n']}",
            "phone_number": f"012{token[:8]}",
            "lincense_number": f"NEW{token[:17]}".upper(),
            "lincense_expiration_date": (
                timezone.localdate() + timedelta(days=365)
            ).isoformat(),
            "branch": company_branch.id,
        }
        payload.update(overrides)
        return payload

    return build_driver_payload
