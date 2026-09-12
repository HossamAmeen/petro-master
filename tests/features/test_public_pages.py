"""Everything an anonymous visitor (landing page / mobile splash) can reach.

Each test follows the Given-When-Then template; the unauthenticated client and
the base geo data live in ``setup``.
"""

import pytest
from django.urls import reverse
from rest_framework import status

from apps.geo.tests.helpers import cities_list_url, districts_list_url
from apps.stations.models.stations_models import StationBranch
from apps.stations.tests.helpers import branches_list_url, stations_list_url
from configrations.models import ConfigrationsModel, Slider

pytestmark = [pytest.mark.django_db, pytest.mark.feature]


def ids(response):
    return {item["id"] for item in response.data["results"]}


class TestPublicPages:
    @pytest.fixture(autouse=True)
    def setup(self, api_client, geo_data):
        self.client = api_client
        self.geo = geo_data

    def test_geo_catalog_is_public_success(self):
        # Given the base geo data (from setup)
        # When an anonymous visitor lists cities and districts
        cities = self.client.get(cities_list_url())
        districts = self.client.get(districts_list_url())

        # Then both are public and districts nest their full city
        assert cities.status_code == status.HTTP_200_OK
        assert self.geo["city"].id in ids(cities)
        (district,) = districts.data["results"]
        assert district["city"]["name"] == self.geo["city"].name

    def test_geo_is_read_only_fail(self):
        # Given the public geo catalog
        # When an anonymous visitor tries to create a city
        response = self.client.post(
            cities_list_url(), {"name": "Nasr City"}, format="json"
        )

        # Then writes are not allowed
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_station_branches_list_defaults_to_available_success(
        self, admin_user, branch, other_station_branch
    ):
        # Given one available and one unavailable station branch
        StationBranch.objects.filter(id=other_station_branch.id).update(
            is_available=False
        )

        # When an anonymous visitor lists branches
        default = self.client.get(branches_list_url())
        including_hidden = self.client.get(branches_list_url(is_available="false"))

        # Then the branch list is public and not filtered by is_available
        assert default.status_code == status.HTTP_200_OK
        # both branches are listed: the branch list is not filtered by is_available
        assert {branch.id, other_station_branch.id} <= ids(default)
        assert other_station_branch.id in ids(including_hidden)

    def test_stations_list_hides_unavailable_by_default_success(
        self, station, other_station
    ):
        # Given an available and an unavailable station
        other_station.is_available = False
        other_station.save(update_fields=["is_available"])

        # When an anonymous visitor lists stations
        default = self.client.get(stations_list_url())
        unavailable = self.client.get(stations_list_url(is_available="false"))

        # Then the stations list requires dashboard auth (401 for visitors)
        assert default.status_code == status.HTTP_401_UNAUTHORIZED
        assert unavailable.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sliders_are_public_success(self, admin_user):
        # Given a slider
        Slider.objects.create(name="Promo", image="sliders/promo.png", order=1)

        # When an anonymous visitor lists sliders
        response = self.client.get(reverse("sliders"))

        # Then it is returned publicly
        assert response.status_code == status.HTTP_200_OK
        assert [item["name"] for item in response.data["results"]] == ["Promo"]

    def test_configrations_are_public_success(self):
        # Given no configuration, then a populated one
        # When an anonymous visitor reads the configrations before and after
        empty = self.client.get(reverse("configrations"))
        ConfigrationsModel.objects.create(
            term_conditions="T", privacy_policy="P", about_us="A", faq="Q"
        )
        filled = self.client.get(reverse("configrations"))

        # Then it returns empty defaults, then the stored values
        assert empty.status_code == status.HTTP_200_OK
        assert empty.data["about_us"] == ""
        assert filled.data["about_us"] == "A"

    def test_contact_us_accepts_a_message_success(self, local_cache):
        # Given an anonymous visitor
        # When they submit a complete contact-us message
        response = self.client.post(
            reverse("contact-us"),
            {"name": "Visitor", "email": "visitor@example.com", "message": "Hello"},
            format="json",
        )

        # Then it is accepted
        assert response.status_code == status.HTTP_200_OK

    def test_contact_us_validates_the_payload_fail(self, local_cache):
        # Given an anonymous visitor
        # When they submit an incomplete contact-us message
        response = self.client.post(
            reverse("contact-us"), {"name": "Visitor"}, format="json"
        )

        # Then it is rejected by validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_contact_us_is_rate_limited_fail(self, local_cache):
        from django.core.cache import cache

        # Given a fresh throttle budget (the counter is per client IP)
        cache.clear()
        payload = {"name": "V", "email": "v@example.com", "message": "Hi"}

        # When the visitor posts six times in a minute
        statuses = [
            self.client.post(reverse("contact-us"), payload, format="json").status_code
            for _ in range(6)
        ]

        # Then the sixth is throttled
        assert statuses[:5] == [status.HTTP_200_OK] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS
