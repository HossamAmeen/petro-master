import pytest
from django.urls import reverse
from rest_framework import status

from apps.stations.models.stations_models import Station

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestStationCreate:
    @pytest.fixture(autouse=True)
    def setup(self, auth_client, station_payload_factory):
        self.auth_client = auth_client
        self.payload_factory = station_payload_factory
        self.url = reverse("stations-list")

    def test_create_without_authentication_fail(self, api_client):
        response = api_client.post(self.url, self.payload_factory(), format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert Station.objects.filter(name="New Station 1").count() == 0

    @pytest.mark.parametrize(
        "role_fixture",
        ["station_owner", "station_worker", "company_owner"],
    )
    def test_create_forbidden_role_fail(self, role_fixture, request, company, station):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker"}:
            client_kwargs["station_id"] = station.id
        existing = set(Station.objects.values_list("id", flat=True))

        response = self.auth_client(user, **client_kwargs).post(
            self.url, self.payload_factory(), format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert set(Station.objects.values_list("id", flat=True)) == existing

    def test_create_as_admin_success(self, admin_user, geo_data):
        payload = self.payload_factory()

        response = self.auth_client(admin_user).post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        created = Station.objects.get(name=payload["name"])
        assert created.address == payload["address"]
        assert created.district_id == geo_data["district"].id
        assert created.balance == 0
        assert created.created_by_id == admin_user.id

    @pytest.mark.parametrize("role_fixture", ["finance_user", "customer_support_user"])
    def test_create_as_dashboard_role_success(self, role_fixture, request):
        user = request.getfixturevalue(role_fixture)
        payload = self.payload_factory()

        response = self.auth_client(user).post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Station.objects.filter(name=payload["name"]).exists()

    def test_create_missing_name_fail(self, admin_user):
        payload = self.payload_factory()
        payload.pop("name")

        response = self.auth_client(admin_user).post(self.url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
