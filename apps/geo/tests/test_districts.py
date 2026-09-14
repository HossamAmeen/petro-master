import pytest
from rest_framework import status

from apps.geo.models import District
from apps.geo.tests.helpers import (
    districts_detail_url,
    districts_list_url,
    returned_ids,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestDistricts:

    def test_list_districts_without_authentication_success(
        self, api_client, geo_data, other_district
    ):
        response = api_client.get(districts_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert {geo_data["district"].id, other_district.id}.issubset(ids)

    def test_list_districts_as_authenticated_user_success(
        self, auth_client, company_owner, company, geo_data
    ):
        response = auth_client(company_owner, company_id=company.id).get(
            districts_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert geo_data["district"].id in returned_ids(response)

    def test_list_districts_payload_nests_city_success(self, api_client, geo_data):
        district = geo_data["district"]
        city = geo_data["city"]

        response = api_client.get(districts_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        listed = {item["id"]: item for item in response.data["results"]}
        row = listed[district.id]
        assert row["id"] == district.id
        assert row["name"] == district.name
        assert row["city"] == {
            "id": city.id,
            "name": city.name,
            "country": geo_data["country"].id,
        }

    def test_list_districts_filter_by_city_success(
        self, api_client, geo_data, other_district, second_cairo_district
    ):
        response = api_client.get(
            districts_list_url(city=geo_data["city"].id, no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert geo_data["district"].id in ids
        assert second_cairo_district.id in ids
        assert other_district.id not in ids

    def test_list_districts_search_by_name_success(
        self, api_client, geo_data, other_district
    ):
        response = api_client.get(
            districts_list_url(search="Al Olaya", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert other_district.id in ids
        assert geo_data["district"].id not in ids

    def test_list_districts_newest_first_success(
        self, api_client, geo_data, other_district
    ):
        response = api_client.get(districts_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        maadi_index = ids.index(geo_data["district"].id)
        olaya_index = ids.index(other_district.id)
        assert olaya_index < maadi_index

    def test_retrieve_district_success(self, api_client, geo_data):
        district = geo_data["district"]
        city = geo_data["city"]

        response = api_client.get(districts_detail_url(district.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == district.id
        assert response.data["name"] == district.name
        assert response.data["city"] == {
            "id": city.id,
            "name": city.name,
            "country": geo_data["country"].id,
        }

    def test_retrieve_unknown_district_fail(self, api_client):
        response = api_client.get(districts_detail_url(999_999))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_district_method_not_allowed_fail(self, api_client, geo_data):
        before = District.objects.count()

        response = api_client.post(
            districts_list_url(),
            {"name": "Heliopolis", "city": geo_data["city"].id},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert District.objects.count() == before

    def test_update_district_method_not_allowed_fail(self, api_client, geo_data):
        district = geo_data["district"]

        response = api_client.patch(
            districts_detail_url(district.id),
            {"name": "Zamalek"},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        district.refresh_from_db()
        assert district.name == "Maadi"

    def test_delete_district_method_not_allowed_fail(self, api_client, geo_data):
        district = geo_data["district"]

        response = api_client.delete(districts_detail_url(district.id))

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert District.objects.filter(pk=district.id).exists()
