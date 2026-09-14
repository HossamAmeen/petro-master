import pytest
from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Car

pytestmark = [pytest.mark.api, pytest.mark.django_db]


REQUIRED_FIELDS = [
    "code",
    "plate_color",
    "color",
    "model_year",
    "brand",
    "is_with_odometer",
    "tank_capacity",
    "permitted_fuel_amount",
    "number_of_fuelings_per_day",
    "number_of_washes_per_month",
    "branch",
]

BALANCE_SOURCES = [
    Car.BalanceSource.CAR,
    Car.BalanceSource.BRANCH,
    Car.BalanceSource.COMPANY,
]


class TestCarCreate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, company_owner, company, car_payload_factory):
        self.owner = company_owner
        self.build_payload = car_payload_factory
        self.client = auth_client(company_owner, company_id=company.id)
        self.url = reverse("cars-list")

    def create(self, payload):
        return self.client.post(self.url, payload, format="json")

    def test_create_without_authentication_fail(self, api_client):
        response = api_client.post(self.url, self.build_payload(), format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Car.objects.count() == 0

    def test_create_car_success(self, company_branch):
        payload = self.build_payload()

        response = self.create(payload)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_car = Car.objects.get(pk=response.data["id"])
        assert created_car.code == payload["code"]
        assert created_car.branch == company_branch
        assert created_car.created_by_id == self.owner.id

    @pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
    def test_create_missing_required_field_fail(self, missing_field):
        payload = self.build_payload()
        payload.pop(missing_field)

        response = self.create(payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.count() == 0

    def test_create_unknown_car_code_fail(self):
        response = self.create(self.build_payload(code="UNKNOWN001"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.count() == 0

    def test_create_duplicate_car_code_fail(self, car_factory, car_code_factory):
        car_code = car_code_factory()
        car_factory(code=car_code.code)

        response = self.create(self.build_payload(car_code=car_code))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.filter(code=car_code.code).count() == 1

    def test_create_permitted_fuel_above_capacity_fail(self):
        response = self.create(
            self.build_payload(tank_capacity=50, permitted_fuel_amount=51)
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.count() == 0

    def test_create_same_primary_and_backup_service_fail(self, service):
        response = self.create(self.build_payload(backup_service=service.id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.count() == 0

    @pytest.mark.parametrize(
        ("field", "invalid_value"),
        [
            ("plate_color", "#INVALID"),
            ("fuel_type", "invalid-fuel"),
        ],
    )
    def test_create_invalid_choice_fail(self, field, invalid_value):
        response = self.create(self.build_payload(**{field: invalid_value}))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.count() == 0

    @pytest.mark.parametrize("balance_source", BALANCE_SOURCES)
    def test_create_car_with_balance_source_success(self, balance_source):
        response = self.create(self.build_payload(balance_source=balance_source))

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_car = Car.objects.get(pk=response.data["id"])
        assert response.data["balance_source"] == balance_source
        assert created_car.balance_source == balance_source
        assert created_car.balance == 0

    def test_create_car_defaults_balance_source_to_car_success(self):
        payload = self.build_payload()
        assert "balance_source" not in payload

        response = self.create(payload)

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created_car = Car.objects.get(pk=response.data["id"])
        assert created_car.balance_source == Car.BalanceSource.CAR
        assert created_car.balance_holder == created_car

    def test_create_car_with_invalid_balance_source_fail(self):
        response = self.create(self.build_payload(balance_source="station"))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Car.objects.count() == 0
