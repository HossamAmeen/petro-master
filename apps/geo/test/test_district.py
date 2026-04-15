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
    return City.objects.create(name="Cairo", country=country)


@pytest.fixture
def district(city):
    return District.objects.create(name="Nasr City", city=city)


@pytest.mark.django_db
class TestDistrict:
    def test_get_districts(self, api_client, district):
        url = reverse("districts-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["results"][0]["name"] == district.name

    def test_get_district_detail(self, api_client, district):
        url = reverse("districts-detail", args=[district.id])
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["name"] == district.name

    def test_get_district_not_found(self, api_client):
        url = reverse("districts-detail", args=[999])
        response = api_client.get(url)
        assert response.status_code == 404

    def test_get_districts_empty(self, api_client):
        url = reverse("districts-list")
        response = api_client.get(url)
        assert response.status_code == 200
        assert response.data["results"] == []

    def test_post_district_not_allowed(self, api_client):
        url = reverse("districts-list")
        response = api_client.post(url, {"name": "New District"})
        assert response.status_code == 405
