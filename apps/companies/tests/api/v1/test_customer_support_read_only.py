import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Car, Company, CompanyBranch, Driver

pytestmark = [pytest.mark.api, pytest.mark.django_db]

BASENAMES = [
    "companies",
    "company-branches",
    "cars",
    "drivers",
    "company-cash-requests",
]
TRACKED_MODELS = [
    Company,
    CompanyBranch,
    Car,
    Driver,
    CompanyCashRequest,
    CompanyKhaznaTransaction,
]


class TestCustomerSupportReadOnlyCompanies:
    """
    Customer support sees what the dashboard sees on the company-side
    viewsets but every write is rejected (403) before it reaches the database.
    """

    @pytest.fixture(autouse=True)
    def setup(
        self,
        auth_client,
        customer_support_user,
        company,
        company_branch,
        company_car,
        company_driver,
        cash_request_factory,
    ):
        self.client = auth_client(customer_support_user)
        self.objects = {
            "companies": company,
            "company-branches": company_branch,
            "cars": company_car,
            "drivers": company_driver,
            "company-cash-requests": cash_request_factory(
                driver=company_driver, company=company
            ),
        }

    def detail_url(self, basename, action="detail"):
        return reverse(f"{basename}-{action}", kwargs={"pk": self.objects[basename].pk})

    def snapshot(self):
        return {
            model.__name__: list(model.objects.order_by("pk").values())
            for model in TRACKED_MODELS
        }

    @pytest.mark.parametrize("basename", BASENAMES)
    def test_list_success(self, basename):
        response = self.client.get(reverse(f"{basename}-list"))

        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.data["results"]}
        assert self.objects[basename].id in ids

    @pytest.mark.parametrize("basename", BASENAMES)
    def test_retrieve_success(self, basename):
        response = self.client.get(self.detail_url(basename))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.objects[basename].id

    @pytest.mark.parametrize(
        "basename, payload_fixture",
        [
            ("companies", "company_payload_factory"),
            ("company-branches", "company_branch_payload_factory"),
            ("cars", "car_payload_factory"),
            ("drivers", "driver_payload_factory"),
            ("company-cash-requests", "cash_request_payload_factory"),
        ],
    )
    def test_create_fail(self, basename, payload_fixture, request):
        payload = request.getfixturevalue(payload_fixture)()
        before = self.snapshot()

        response = self.client.post(reverse(f"{basename}-list"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    @pytest.mark.parametrize(
        "basename, payload",
        [
            ("companies", {"name": "Renamed"}),
            ("company-branches", {"name": "Renamed"}),
            ("cars", {"plate_number": "9999"}),
            ("drivers", {"name": "Renamed"}),
        ],
    )
    @pytest.mark.parametrize("method", ["patch", "put"])
    def test_update_fail(self, method, basename, payload):
        before = self.snapshot()

        response = getattr(self.client, method)(
            self.detail_url(basename), payload, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    @pytest.mark.parametrize("basename", BASENAMES)
    def test_delete_fail(self, basename):
        before = self.snapshot()

        response = self.client.delete(self.detail_url(basename))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    def test_car_update_balance_fail(self):
        before = self.snapshot()

        response = self.client.post(
            self.detail_url("cars", action="update_balance"),
            {"amount": "10.00", "type": "add"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before
