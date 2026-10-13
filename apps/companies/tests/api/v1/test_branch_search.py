import pytest
from django.urls import reverse
from rest_framework import status

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestCompanyBranchSearch:
    def test_search_without_match_returns_nothing_success(
        self, auth_client, admin_user, company_branch
    ):
        response = auth_client(admin_user).get(
            reverse("company-branches-list"), {"search": "zzz-no-such-record"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_search_by_name_success(self, auth_client, admin_user, company_branch):
        response = auth_client(admin_user).get(
            reverse("company-branches-list"), {"search": company_branch.name}
        )

        assert company_branch.id in [row["id"] for row in response.data["results"]]
