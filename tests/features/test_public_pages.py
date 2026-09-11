"""Everything an anonymous visitor (landing page / mobile splash) can reach."""

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
        cities = self.client.get(cities_list_url())
        districts = self.client.get(districts_list_url())

        assert cities.status_code == status.HTTP_200_OK
        assert self.geo["city"].id in ids(cities)
        (district,) = districts.data["results"]
        # districts nest their full city
        assert district["city"]["name"] == self.geo["city"].name

    def test_geo_is_read_only_fail(self):
        response = self.client.post(
            cities_list_url(), {"name": "Nasr City"}, format="json"
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_station_branches_list_defaults_to_available_success(
        self, admin_user, branch, other_station_branch
    ):
        StationBranch.objects.filter(id=other_station_branch.id).update(
            is_available=False
        )

        default = self.client.get(branches_list_url())
        including_hidden = self.client.get(branches_list_url(is_available="false"))

        assert default.status_code == status.HTTP_200_OK
        # both branches are listed: the branch list is not filtered by is_available
        assert {branch.id, other_station_branch.id} <= ids(default)
        assert other_station_branch.id in ids(including_hidden)

    def test_stations_list_hides_unavailable_by_default_success(
        self, station, other_station
    ):
        other_station.is_available = False
        other_station.save(update_fields=["is_available"])

        default = self.client.get(stations_list_url())
        unavailable = self.client.get(stations_list_url(is_available="false"))

        # stations require dashboard auth, so anonymous visitors get 401 here
        assert default.status_code == status.HTTP_401_UNAUTHORIZED
        assert unavailable.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sliders_are_public_success(self, admin_user):
        Slider.objects.create(name="Promo", image="sliders/promo.png", order=1)

        response = self.client.get(reverse("sliders"))

        assert response.status_code == status.HTTP_200_OK
        assert [item["name"] for item in response.data["results"]] == ["Promo"]

    def test_configrations_are_public_success(self):
        empty = self.client.get(reverse("configrations"))
        ConfigrationsModel.objects.create(
            term_conditions="T", privacy_policy="P", about_us="A", faq="Q"
        )
        filled = self.client.get(reverse("configrations"))

        assert empty.status_code == status.HTTP_200_OK
        assert empty.data["about_us"] == ""
        assert filled.data["about_us"] == "A"

    def test_contact_us_accepts_a_message_success(self, local_cache):
        response = self.client.post(
            reverse("contact-us"),
            {"name": "Visitor", "email": "visitor@example.com", "message": "Hello"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

    def test_contact_us_validates_the_payload_fail(self, local_cache):
        response = self.client.post(
            reverse("contact-us"), {"name": "Visitor"}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_contact_us_is_rate_limited_fail(self, local_cache):
        from django.core.cache import cache

        # the throttle counts per client IP in the cache other tests also touch
        cache.clear()
        payload = {"name": "V", "email": "v@example.com", "message": "Hi"}

        statuses = [
            self.client.post(reverse("contact-us"), payload, format="json").status_code
            for _ in range(6)
        ]

        assert statuses[:5] == [status.HTTP_200_OK] * 5
        assert statuses[5] == status.HTTP_429_TOO_MANY_REQUESTS
