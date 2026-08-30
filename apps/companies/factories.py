import random
import uuid
from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from faker import Faker

from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import (
    Car,
    CarCode,
    Company,
    CompanyBranch,
    Driver,
)
from apps.companies.models.operation_model import CarOperation
from apps.geo.models import City, Country, District
from apps.notifications.models import Notification
from apps.stations.models.stations_models import (
    Service,
    Station,
    StationBranch,
    StationBranchService,
    StationService,
)
from apps.users.models import (
    CompanyBranchManager,
    CompanyUser,
    FirebaseToken,
    StationBranchManager,
    StationOwner,
    Supervisor,
    User,
    Worker,
)

fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    phone_number = factory.Sequence(lambda n: f"010000{n:05d}")
    role = User.UserRoles.Admin
    password = factory.PostGenerationMethodCall("set_password", "password123")


class AdminUserFactory(UserFactory):
    is_staff = True
    is_superuser = True


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country

    name = factory.Sequence(lambda n: f"Country {n}")
    code = factory.Sequence(lambda n: f"C{n:02}")


class CityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = City

    name = factory.Faker("city")  # Generates a random city name
    country = factory.SubFactory(CountryFactory)


class DistrictFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = District

    name = factory.Faker("street_name")  # Generates a random district name
    city = factory.SubFactory(CityFactory)  # Ensures city exists


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Faker("company")
    address = factory.Faker("address")
    balance = factory.LazyFunction(
        lambda: Decimal(random.uniform(1000, 100000)).quantize(Decimal("0.01"))
    )
    email = factory.Faker("company_email")
    phone_number = factory.Faker("phone_number")
    district = factory.LazyFunction(lambda: District.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CompanyBranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompanyBranch

    name = factory.Faker("company")
    email = factory.Faker("company_email")
    phone_number = factory.Faker("phone_number")
    address = factory.Faker("address")
    company = factory.LazyFunction(lambda: Company.objects.order_by("?").first())
    district = factory.LazyFunction(lambda: District.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CarFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Car

    code = factory.LazyFunction(lambda: str(uuid.uuid4())[:10].upper())
    plate_number = str(factory.Faker("license_plate"))[:4]
    plate_character = str(factory.Faker("license_plate_character"))[:4]
    plate_color = factory.LazyAttribute(lambda _: random.choice(Car.PlateColor.values))
    color = factory.LazyAttribute(lambda _: random.choice(Car.PlateColor.values))
    license_expiration_date = factory.Faker("future_date")
    model_year = factory.Faker("year")
    brand = factory.LazyAttribute(lambda _: fake.company()[:24])
    is_with_odometer = factory.Faker("boolean")
    tank_capacity = factory.LazyAttribute(
        lambda _: fake.random_int(min=50, max=100)
    )  # Tank capacity between 50-100 liters
    permitted_fuel_amount = factory.LazyAttribute(
        lambda obj: fake.random_int(min=10, max=obj.tank_capacity - 10)
    )  # Always less than tank_capacity
    fuel_type = factory.LazyFunction(lambda: random.choice(Car.FuelType.values))
    number_of_fuelings_per_day = factory.LazyFunction(lambda: random.randint(1, 5))
    fuel_allowed_days = factory.LazyFunction(
        lambda: random.sample(Car.FuelAllowedDay.values, k=3)
    )
    balance = factory.LazyFunction(
        lambda: Decimal(random.uniform(100, 5000)).quantize(Decimal("0.01"))
    )
    city = factory.LazyFunction(lambda: City.objects.order_by("?").first())
    branch = factory.LazyFunction(lambda: CompanyBranch.objects.order_by("?").first())
    number_of_washes_per_month = factory.LazyFunction(lambda: random.randint(1, 10))
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CarCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CarCode

    code = factory.Sequence(lambda number: f"CAR{number:07d}")
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Driver

    name = factory.Faker("name")
    phone_number = factory.Sequence(lambda n: f"015000{n:05d}")
    code = factory.Sequence(lambda n: f"DRV{n:07d}")
    lincense_number = factory.Sequence(lambda n: f"LIC{n:07d}")
    lincense_expiration_date = factory.Faker("future_date")
    branch = factory.LazyFunction(lambda: CompanyBranch.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    description = factory.Faker("text")
    is_read = factory.Faker("boolean")
    title = factory.Faker("sentence", nb_words=3)
    type = factory.Faker("word")
    user = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class StationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Station

    name = factory.Faker("company")
    address = factory.Faker("address")
    lat = factory.Faker("latitude")
    lang = factory.Faker("longitude")
    district = factory.LazyFunction(lambda: District.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class StationBranchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StationBranch

    name = factory.Faker("company")
    address = factory.Faker("address")
    lat = factory.Faker("latitude")
    lang = factory.Faker("longitude")
    district = factory.LazyFunction(lambda: District.objects.order_by("?").first())
    station = factory.LazyFunction(lambda: Station.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class ServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Service

    name = factory.Faker("company")
    type = factory.LazyFunction(lambda: random.choice(Service.ServiceType.values))
    cost = factory.LazyFunction(
        lambda: Decimal(random.uniform(100, 5000)).quantize(Decimal("0.01"))
    )
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class StationServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StationService

    service = factory.LazyFunction(lambda: Service.objects.order_by("?").first())
    station = factory.LazyFunction(lambda: Station.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class StationBranchServiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StationBranchService

    service = factory.LazyFunction(lambda: Service.objects.order_by("?").first())
    station_branch = factory.LazyFunction(
        lambda: StationBranch.objects.order_by("?").first()
    )
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CompanyUserFactory(UserFactory):
    class Meta:
        model = CompanyUser

    name = factory.Faker("name")
    email = factory.Faker("company_email")
    phone_number = factory.Faker("phone_number")
    role = User.UserRoles.CompanyOwner
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    company = factory.LazyFunction(lambda: Company.objects.order_by("?").first())


class StationOwnerFactory(UserFactory):
    class Meta:
        model = StationOwner

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"station-owner-{n}@example.com")
    phone_number = factory.Sequence(lambda n: f"011000{n:05d}")
    role = User.UserRoles.StationOwner
    station = factory.SubFactory(StationFactory)
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class StationBranchManagerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StationBranchManager

    station_branch = factory.SubFactory(StationBranchFactory)
    user = factory.SubFactory(StationOwnerFactory)
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class SupervisorFactory(UserFactory):
    class Meta:
        model = Supervisor

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"supervisor-{n}@example.com")
    phone_number = factory.Sequence(lambda n: f"012000{n:05d}")
    role = User.UserRoles.Supervisor
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CompanyBranchManagerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompanyBranchManager

    company_branch = factory.SubFactory(CompanyBranchFactory)
    user = factory.SubFactory(CompanyUserFactory)
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class WorkerFactory(UserFactory):
    class Meta:
        model = Worker

    name = factory.Faker("name")
    email = factory.Faker("company_email")
    phone_number = factory.Faker("phone_number")
    role = User.UserRoles.StationWorker
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    station_branch = factory.LazyFunction(
        lambda: StationBranch.objects.order_by("?").first()
    )


class FirebaseTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FirebaseToken

    user = factory.SubFactory(UserFactory)
    token = factory.Sequence(lambda n: f"firebase-token-{n}")


class CompanyCashRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompanyCashRequest

    driver = factory.SubFactory(DriverFactory)
    amount = factory.LazyFunction(
        lambda: Decimal(random.uniform(100, 5000)).quantize(Decimal("0.01"))
    )


class CarOperationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CarOperation

    amount = factory.LazyFunction(lambda: random.uniform(100, 5000))
    unit = factory.LazyFunction(lambda: random.choice(Service.ServiceUnit.values))
    car_meter = factory.LazyFunction(lambda: random.randint(10000, 100000))
    cost = factory.LazyFunction(lambda: random.uniform(100, 5000))
    fuel_consumption_rate = factory.LazyFunction(lambda: random.randint(9, 99))
    fuel_type = factory.LazyFunction(lambda: random.choice(Car.FuelType.values))
    status = factory.LazyFunction(
        lambda: random.choice(CarOperation.OperationStatus.values)
    )
    code = factory.LazyFunction(lambda: str(uuid.uuid4())[:10].upper())
    start_time = factory.LazyFunction(lambda: timezone.now())
    end_time = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    duration = factory.LazyFunction(lambda: random.uniform(10, 60))

    car = factory.LazyFunction(lambda: Car.objects.order_by("?").first())
    driver = factory.LazyFunction(lambda: Driver.objects.order_by("?").first())
    station_branch = factory.LazyFunction(
        lambda: StationBranch.objects.order_by("?").first()
    )
    worker = factory.LazyFunction(lambda: Worker.objects.order_by("?").first())
    service = factory.LazyFunction(lambda: Service.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CompanyKhaznaTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompanyKhaznaTransaction

    amount = factory.LazyFunction(lambda: random.uniform(100, 5000))
    is_incoming = factory.LazyFunction(lambda: random.choice([True, False]))
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    company = factory.LazyFunction(lambda: Company.objects.order_by("?").first())
    reference_code = factory.LazyFunction(lambda: str(uuid.uuid4())[:10].upper())
    for_what = factory.LazyFunction(
        lambda: random.choice(CompanyKhaznaTransaction.ForWhat.values)
    )
    status = factory.LazyFunction(
        lambda: random.choice(CompanyKhaznaTransaction.TransactionStatus.values)
    )
    # reviewed_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    description = factory.Faker("text")
    method = factory.LazyFunction(
        lambda: random.choice(CompanyKhaznaTransaction.TransactionMethod.values)
    )
    approved_at = factory.LazyFunction(
        lambda: timezone.now() if random.choice([True, False]) else None
    )
    photo = factory.LazyFunction(lambda: None)
    is_unpaid = factory.LazyFunction(lambda: random.choice([True, False]))
