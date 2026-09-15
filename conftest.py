from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.geo.models import City, Country, District

pytest_plugins = [
    "apps.users.tests.conftest",
    "apps.companies.tests.conftest",
    "apps.stations.tests.conftest",
]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client():
    """Build a client per call so `api_client` always stays unauthenticated."""

    def _auth_client(user, station_id=None, *, company_id=None):
        access_token = AccessToken.for_user(user)
        if company_id is not None:
            access_token["company_id"] = company_id
        if station_id is not None:
            access_token["station_id"] = station_id
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(access_token)}")
        return client

    return _auth_client


@pytest.fixture
def role_client(request, auth_client):
    """
    Client for a user fixture given by name, with the `company_id` /
    `station_id` claim its role logs in with, so role matrices can be
    parametrized over fixture names.
    """

    def _role_client(user_fixture):
        user = request.getfixturevalue(user_fixture)
        claims = {}
        if hasattr(user, "company_id"):
            claims["company_id"] = user.company_id
        if hasattr(user, "station_id"):
            claims["station_id"] = user.station_id
        if hasattr(user, "station_branch"):
            claims["station_id"] = user.station_branch.station_id
        return auth_client(user, **claims)

    return _role_client


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
