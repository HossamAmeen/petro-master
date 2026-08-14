import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from apps.geo.models import City, Country, District
from unittest.mock import patch

pytest_plugins = [
    "apps.users.test.conftest",
    "apps.companies.tests.conftest",
    "apps.stations.tests.conftest",
]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    def _auth_client(user, station_id=None, *, company_id=None):
        access_token = AccessToken.for_user(user)
        if company_id is not None:
            access_token["company_id"] = company_id
        if station_id is not None:
            access_token["station_id"] = station_id
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(access_token)}")
        return api_client

    return _auth_client


@pytest.fixture
def geo_data(db):
    country = Country.objects.create(name="Egypt", code="EG")
    city = City.objects.create(name="Cairo", country=country)
    district = District.objects.create(name="Maadi", city=city)
    return {"country": country, "city": city, "district": district}


@pytest.fixture(autouse=True)
def mock_firebase_notifications():
    """Prevent tests from issuing Firebase Cloud Messaging requests."""
    with patch("apps.notifications.fcm_manager.FCMManager.send_fcm_message") as send:
        yield send
