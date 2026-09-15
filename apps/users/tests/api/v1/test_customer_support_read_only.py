import pytest
from django.urls import reverse
from rest_framework import status

from apps.users.models import CompanyBranchManager, StationBranchManager, User

pytestmark = [pytest.mark.api, pytest.mark.django_db]

VIEWSETS = [
    ("company-owners", "company_owner", "company_owner_payload_factory"),
    (
        "company-branch-managers",
        "company_branch_manager",
        "company_branch_manager_payload_factory",
    ),
    ("station-owners", "station_owner", "station_owner_payload_factory"),
    (
        "station-branch-managers",
        "branch_manager",
        "station_branch_manager_payload_factory",
    ),
    ("workers", "station_worker", "worker_payload_factory"),
]
BASENAMES = [basename for basename, _, _ in VIEWSETS]
TRACKED_MODELS = [User, CompanyBranchManager, StationBranchManager]


class TestCustomerSupportReadOnlyUsers:
    """
    Customer support may list the company and station staff the dashboard
    manages, but cannot create, edit, or delete any of them.
    """

    @pytest.fixture(autouse=True)
    def setup(self, request, auth_client, customer_support_user):
        self.client = auth_client(customer_support_user)
        self.objects = {
            basename: request.getfixturevalue(user_fixture)
            for basename, user_fixture, _ in VIEWSETS
        }
        self.payload_factories = {
            basename: request.getfixturevalue(payload_fixture)
            for basename, _, payload_fixture in VIEWSETS
        }

    def detail_url(self, basename):
        return reverse(f"{basename}-detail", kwargs={"pk": self.objects[basename].pk})

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

    @pytest.mark.parametrize("basename", BASENAMES)
    def test_create_fail(self, basename):
        payload = self.payload_factories[basename]()
        before = self.snapshot()

        response = self.client.post(reverse(f"{basename}-list"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    @pytest.mark.parametrize("basename", BASENAMES)
    @pytest.mark.parametrize("method", ["patch", "put"])
    def test_update_fail(self, method, basename):
        before = self.snapshot()

        response = getattr(self.client, method)(
            self.detail_url(basename), {"name": "Renamed"}, format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before

    @pytest.mark.parametrize("basename", BASENAMES)
    def test_delete_fail(self, basename):
        before = self.snapshot()

        response = self.client.delete(self.detail_url(basename))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert self.snapshot() == before
