import factory
import random
import uuid
from faker import Faker
from decimal import Decimal
from apps.geo.models import District, City
from apps.companies.models import Company, CompanyBranch, Car, Driver
from apps.users.models import User
from apps.notifications.models import Notification
fake = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    name = factory.Faker("name")
    email = factory.Faker("company_email")
    phone_number = factory.Faker("phone_number")
    role = factory.LazyFunction(lambda: ["admin", "company_owner", "branch_manager", "driver",
                                         "station_manager", "station_employee", "station_worker"]
                                        [random.randint(0, 6)])
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Faker("company")
    address = factory.Faker("address")
    balance = factory.LazyFunction(lambda: Decimal(random.uniform(1000, 100000)).quantize(Decimal("0.01")))
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
    company = factory.SubFactory(CompanyFactory)
    district = factory.LazyFunction(lambda: District.objects.order_by("?").first())
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class CarFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Car

    code = factory.LazyFunction(lambda: str(uuid.uuid4())[:10].upper())
    plate = factory.Faker("license_plate")
    plate_color = factory.LazyAttribute(lambda _: fake.color_name()[:9])
    color = factory.LazyAttribute(lambda _: fake.color_name()[:9])
    license_expiration_date = factory.Faker("future_date")
    model_year = factory.Faker("year")
    brand = factory.LazyAttribute(lambda _: fake.company()[:24])
    is_with_odometer = factory.Faker("boolean")
    tank_capacity = factory.LazyAttribute(lambda _: fake.random_int(min=50, max=100))  # Tank capacity between 50-100 liters
    permitted_fuel_amount = factory.LazyAttribute(lambda obj: fake.random_int(min=10, max=obj.tank_capacity - 10))  # Always less than tank_capacity
    fuel_type = factory.LazyFunction(lambda: random.choice(Car.FuelType.values))
    number_of_fuelings_per_day = factory.LazyFunction(lambda: random.randint(1, 5))
    fuel_allowed_days = factory.LazyFunction(lambda: random.sample(Car.FuelAllowedDay.values, k=3))
    balance = factory.LazyFunction(lambda: Decimal(random.uniform(100, 5000)).quantize(Decimal("0.01")))
    city = factory.LazyFunction(lambda: City.objects.order_by("?").first())
    branch = factory.SubFactory(CompanyBranchFactory)
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class DriverFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Driver

    name = factory.Faker("name")
    phone_number = factory.Faker("phone_number")
    code = factory.LazyFunction(lambda: f"DR-{uuid.uuid4().hex[:10].upper()}")
    lincense_number = factory.Faker("ssn")
    lincense_expiration_date = factory.Faker("future_date")
    branch = factory.SubFactory(CompanyBranchFactory)
    created_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())
    updated_by = factory.LazyFunction(lambda: User.objects.order_by("?").first())


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    description = factory.Faker('text')
    is_read = factory.Faker('boolean')
    title = factory.Faker('sentence', nb_words=3)
    type = factory.Faker('word')
    user = factory.SubFactory(UserFactory)
