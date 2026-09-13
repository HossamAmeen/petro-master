import pytest
from rest_framework import status

from apps.geo.models import City
from apps.geo.tests.helpers import cities_detail_url, cities_list_url, returned_ids

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCities:

    def test_list_cities_without_authentication_success(
        self, api_client, geo_data, other_city
    ):
        response = api_client.get(cities_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert {geo_data["city"].id, other_city.id}.issubset(ids)

    def test_list_cities_as_authenticated_user_success(
        self, auth_client, admin_user, geo_data
    ):
        response = auth_client(admin_user).get(cities_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        assert geo_data["city"].id in returned_ids(response)

    def test_list_cities_payload_fields_success(self, api_client, geo_data):
        city = geo_data["city"]

        response = api_client.get(cities_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[city.id]
        assert row == {
            "id": city.id,
            "name": city.name,
            "country": geo_data["country"].id,
        }

    def test_list_cities_filter_by_country_success(
        self, api_client, geo_data, other_city, other_country
    ):
        response = api_client.get(
            cities_list_url(country=geo_data["country"].id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert geo_data["city"].id in ids
        assert other_city.id not in ids

    def test_list_cities_search_by_name_success(self, api_client, geo_data, other_city):
        response = api_client.get(cities_list_url(search="Riyadh", no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert other_city.id in ids
        assert geo_data["city"].id not in ids

    def test_list_cities_newest_first_success(self, api_client, geo_data, other_city):
        response = api_client.get(cities_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        cairo_index = ids.index(geo_data["city"].id)
        riyadh_index = ids.index(other_city.id)
        assert riyadh_index < cairo_index

    def test_retrieve_city_success(self, api_client, geo_data):
        city = geo_data["city"]

        response = api_client.get(cities_detail_url(city.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "id": city.id,
            "name": city.name,
            "country": geo_data["country"].id,
        }

    def test_retrieve_unknown_city_fail(self, api_client):
        response = api_client.get(cities_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_city_method_not_allowed_fail(self, api_client, geo_data):
        before = City.objects.count()

        response = api_client.post(
            cities_list_url(),
            {"name": "Alexandria", "country": geo_data["country"].id},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert City.objects.count() == before

    def test_update_city_method_not_allowed_fail(self, api_client, geo_data):
        city = geo_data["city"]

        response = api_client.patch(
            cities_detail_url(city.id),
            {"name": "Giza"},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        city.refresh_from_db()
        assert city.name == "Cairo"

    def test_delete_city_method_not_allowed_fail(self, api_client, geo_data):
        city = geo_data["city"]

        response = api_client.delete(cities_detail_url(city.id))

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert City.objects.filter(pk=city.id).exists()
