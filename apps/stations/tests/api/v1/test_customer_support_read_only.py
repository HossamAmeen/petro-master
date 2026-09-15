import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.companies.models.operation_model import CarOperation
from apps.stations.models.service_models import Service
from apps.stations.models.stations_models import (
    Station,
    StationBranch,
    StationBranchService,
)
from apps.stations.tests.helpers import gas_url
from apps.users.models import StationBranchManager

pytestmark = [pytest.mark.api, pytest.mark.django_db]

TRACKED_MODELS = [
    Station,
    StationBranch,
    StationBranchService,
    StationBranchManager,
    Service,
    CarOperation,
    StationKhaznaTransaction,
]


class TestCustomerSupportReadOnlyStations:
    """
    Customer support sees what the dashboard sees on the station-side
    viewsets but every write is rejected (403) before it reaches the database.
    """

    @pytest.fixture(autouse=True)
    def setup(self, auth_client, customer_support_user, station, branch, service):
        self.client = auth_client(customer_support_user)
        self.objects = {
            "stations": station,
            "station-branches": branch,
            "services": service,
        }

    def detail_url(self, basename, action="detail"):
        return reverse(f"{basename}-{action}", kwargs={"pk": self.objects[basename].pk})

    def snapshot(self):
        return {
            model.__name__: list(model.objects.order_by("pk").values())
            for model in TRACKED_MODELS
        }

    @pytest.mark.parametrize("basename", ["stations", "services"])
    def test_list_success(self, basename):
        response = self.client.get(reverse(f"{basename}-list"))

        assert response.status_code == status.HTTP_200_OK
        ids = {row["id"] for row in response.data["results"]}
        assert self.objects[basename].id in ids

    @pytest.mark.parametrize("basename", ["stations", "station-branches", "services"])
    def test_retrieve_success(self, basename):
        response = self.client.get(self.detail_url(basename))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == self.objects[basename].id

    @pytest.mark.parametrize(
        "basename, payload_fixture",
        [
            ("stations", "station_payload_factory"),
            ("station-branches", "station_branch_payload_factory"),
        ],
    )
    def test_create_fail(self, basename, payload_fixture, request):
        payload = request.getfixturevalue(payload_fixture)()
        before = self.snapshot()

        response = self.client.post(reverse(f"{basename}-list"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    def test_create_service_fail(self):
        before = self.snapshot()

        response = self.client.post(
            reverse("services-list"),
            {"name": "Gasoline 95", "unit": "litre", "type": "petrol", "cost": "12"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    @pytest.mark.parametrize(
        "basename, payload",
        [
            ("stations", {"name": "Renamed"}),
            ("station-branches", {"name": "Renamed"}),
            ("services", {"name": "Renamed"}),
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

    @pytest.mark.parametrize("basename", ["stations", "station-branches", "services"])
    def test_delete_fail(self, basename):
        before = self.snapshot()

        response = self.client.delete(self.detail_url(basename))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    @pytest.mark.parametrize(
        "action", ["assign-services", "add-service", "delete-service"]
    )
    def test_branch_service_actions_fail(
        self, action, branch_petrol_service, other_service
    ):
        before = self.snapshot()

        response = self.client.post(
            self.detail_url("station-branches", action=action),
            {"services": [other_service.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    def test_branch_assign_managers_fail(self, branch_manager, station_owner):
        before = self.snapshot()

        response = self.client.post(
            self.detail_url("station-branches", action="assign-managers"),
            {"managers": [station_owner.id]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    def test_gas_operation_update_fail(self, gas_operation):
        before = self.snapshot()

        response = self.client.patch(
            gas_url(gas_operation.id),
            {"start_time": timezone.localtime().isoformat()},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before
