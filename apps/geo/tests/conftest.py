import pytest

from apps.geo.models import City, Country, District


@pytest.fixture
def other_country(db):
    return Country.objects.create(name="Saudi Arabia", code="SA")


@pytest.fixture
def other_city(db, other_country):
    return City.objects.create(name="Riyadh", country=other_country)


@pytest.fixture
def other_district(db, other_city):
    return District.objects.create(name="Al Olaya", city=other_city)


@pytest.fixture
def second_cairo_district(db, geo_data):
    return District.objects.create(name="Nasr City", city=geo_data["city"])
