import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestDashboardUserSearch:
    def test_search_without_match_returns_nothing_success(self, auth_client, admin_user):
        response = auth_client(admin_user).get(
            reverse("users-list"), {"search": "zzz-no-such-record"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_search_by_name_success(self, auth_client, admin_user):
        response = auth_client(admin_user).get(
            reverse("users-list"), {"search": admin_user.name}
        )

        assert admin_user.id in [row["id"] for row in response.data["results"]]
