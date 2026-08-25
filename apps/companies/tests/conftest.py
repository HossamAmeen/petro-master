from decimal import Decimal

import pytest

from apps.companies.factories import (
    CarCodeFactory,
    CarFactory,
    CompanyBranchFactory,
    CompanyFactory,
)
from apps.companies.models.company_models import Car, Company, CompanyBranch
from apps.users.models import CompanyBranchManager, CompanyUser, User


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
