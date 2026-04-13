import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.geo.models import City, Country, District


@pytest.fixture
def country():
    return Country.objects.create(name="Egypt")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def city(country):
    return City.objects.create(name="Cairo", country=country)


@pytest.fixture
def district(city):
    return District.objects.create(name="Nasr City", city=city)


@pytest.fixture
def cities_url():
    return "/api/v1/geo/cities/"


@pytest.mark.django_db
def test_get_cities(api_client, city, cities_url):
    response = api_client.get(cities_url)
    assert response.status_code == 200
    assert any(c["name"] == "Cairo" for c in response.data["results"])


@pytest.mark.django_db
def test_get_city_detail(api_client, city):

    url = reverse("cities-detail", args=[city.id])
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["name"] == "Cairo"


@pytest.mark.django_db
def test_get_city_not_found(api_client):

    url = reverse("cities-detail", args=[999])
    response = api_client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_get_cities_empty(api_client, cities_url):

    response = api_client.get(cities_url)

    assert response.status_code == 200
    assert response.data["results"] == []


@pytest.mark.django_db
def test_post_city_not_allowed(api_client, cities_url):

    response = api_client.post(cities_url, {"name": "Alex"})

    assert response.status_code == 405
