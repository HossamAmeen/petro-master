import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.geo.models import City, Country, District

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
    def _auth_client(user, station_id=None):
        access_token = AccessToken.for_user(user)
        if station_id:
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
