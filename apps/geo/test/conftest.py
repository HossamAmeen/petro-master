import pytest
from rest_framework.test import APIClient

from apps.geo.models import City, Country, District


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def country():
    return Country.objects.create(name="Egypt")


@pytest.fixture
def city(country):
    return City.objects.create(name="Cairo", country=country)


@pytest.fixture
def district(city):
    return District.objects.create(name="Nasr City", city=city)
