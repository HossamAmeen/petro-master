import pytest
from django.urls import reverse
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
    return City.objects.create(name="cairo", country=country)


@pytest.fixture
def district(city):
    return District.objects.create(name="Nasr City", city=city)


@pytest.mark.django_db
def test_get_cities(api_client, city):
    url = reverse("cities-list")
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data["results"][0]["name"] == city.name


@pytest.mark.django_db
def test_get_city_detail(api_client, city):

    url = reverse("cities-detail", args=[city.id])
    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["name"] == city.name


@pytest.mark.django_db
def test_get_city_not_found(api_client):

    url = reverse("cities-detail", args=[999])
    response = api_client.get(url)

    assert response.status_code == 404


@pytest.mark.django_db
def test_get_cities_empty(api_client):
    url = reverse("cities-list")

    response = api_client.get(url)

    assert response.status_code == 200
    assert response.data["results"] == []


@pytest.mark.django_db
def test_post_city_not_allowed(api_client):
    url = reverse("cities-list")

    response = api_client.post(url, {"name": "Alex"})

    assert response.status_code == 405
