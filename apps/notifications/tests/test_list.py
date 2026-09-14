import pytest
from rest_framework import status

from apps.notifications.models import Notification
from apps.notifications.tests.helpers import notifications_list_url, returned_ids

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestList:

    def test_list_without_authentication_fail(self, api_client):
        response = api_client.get(notifications_list_url())

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.parametrize(
        "role_fixture",
        [
            "admin_user",
            "finance_user",
            "company_owner",
            "station_owner",
            "station_worker",
        ],
    )
    def test_list_authenticated_role_success(
        self, role_fixture, request, auth_client, company, station
    ):
        user = request.getfixturevalue(role_fixture)
        client_kwargs = {}
        if role_fixture == "company_owner":
            client_kwargs["company_id"] = company.id
        if role_fixture in {"station_owner", "station_worker"}:
            client_kwargs["station_id"] = station.id

        response = auth_client(user, **client_kwargs).get(notifications_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert "unread_count" in response.data

    def test_list_is_user_scoped_success(
        self, auth_client, admin_user, finance_user, notification_factory
    ):
        mine = notification_factory(user=admin_user, title="Admin note")
        notification_factory(user=finance_user, title="Finance note")

        response = auth_client(admin_user).get(
            notifications_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = returned_ids(response)
        assert mine.id in ids
        assert ids == {mine.id}

    def test_list_payload_fields_success(
        self, auth_client, admin_user, notification_factory
    ):
        note = notification_factory(
            user=admin_user,
            title="Balance updated",
            description="Branch transfer",
            type=Notification.NotificationType.MONEY,
            is_read=False,
            is_success=True,
            url="https://example.com/n/1",
        )

        response = auth_client(admin_user).get(
            notifications_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        row = response.data["results"][0]
        assert row["id"] == note.id
        assert row["title"] == "Balance updated"
        assert row["description"] == "Branch transfer"
        assert row["type"] == Notification.NotificationType.MONEY
        assert row["is_read"] is False
        assert row["is_success"] is True
        assert row["user"] == admin_user.id
        assert row["url"] == "https://example.com/n/1"
        assert "created" in row
        assert "modified" in row

    def test_list_newest_first_success(
        self, auth_client, admin_user, notification_factory
    ):
        first = notification_factory(user=admin_user, title="Older")
        second = notification_factory(user=admin_user, title="Newer")

        response = auth_client(admin_user).get(
            notifications_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in response.data["results"]]
        assert ids == [second.id, first.id]

    def test_list_dashboard_unread_count_success(
        self, auth_client, admin_user, notification_factory
    ):
        notification_factory(user=admin_user, is_read=False)
        notification_factory(user=admin_user, is_read=False)
        notification_factory(user=admin_user, is_read=True)

        response = auth_client(admin_user).get(
            notifications_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["unread_count"] == 2
        assert len(response.data["results"]) == 3

    def test_list_non_dashboard_unread_count_is_zero_success(
        self, auth_client, company_owner, company, notification_factory
    ):
        notification_factory(user=company_owner, is_read=False)
        notification_factory(user=company_owner, is_read=False)

        response = auth_client(company_owner, company_id=company.id).get(
            notifications_list_url(no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["unread_count"] == 0
        assert len(response.data["results"]) == 2

    @pytest.mark.parametrize(
        "role_fixture",
        ["finance_user", "customer_support_user"],
    )
    def test_list_other_dashboard_roles_include_unread_count_success(
        self, role_fixture, request, auth_client, notification_factory
    ):
        user = request.getfixturevalue(role_fixture)
        notification_factory(user=user, is_read=False)

        response = auth_client(user).get(notifications_list_url(no_paginate="true"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["unread_count"] == 1

    def test_list_filter_is_read_success(
        self, auth_client, admin_user, notification_factory
    ):
        unread = notification_factory(user=admin_user, is_read=False)
        notification_factory(user=admin_user, is_read=True)

        response = auth_client(admin_user).get(
            notifications_list_url(is_read="false", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {unread.id}

    def test_list_filter_type_iexact_success(
        self, auth_client, admin_user, notification_factory
    ):
        fuel = notification_factory(
            user=admin_user, type=Notification.NotificationType.FUEL
        )
        notification_factory(user=admin_user, type=Notification.NotificationType.MONEY)

        response = auth_client(admin_user).get(
            notifications_list_url(type="FUEL", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {fuel.id}

    def test_list_search_title_success(
        self, auth_client, admin_user, notification_factory
    ):
        match = notification_factory(user=admin_user, title="UniquePetrolAlert")
        notification_factory(user=admin_user, title="Other title")

        response = auth_client(admin_user).get(
            notifications_list_url(search="UniquePetrolAlert", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {match.id}

    def test_list_search_description_success(
        self, auth_client, admin_user, notification_factory
    ):
        match = notification_factory(
            user=admin_user, title="Note", description="zebra-meter-reading"
        )
        notification_factory(user=admin_user, description="something else")

        response = auth_client(admin_user).get(
            notifications_list_url(search="zebra-meter-reading", no_paginate="true")
        )

        assert response.status_code == status.HTTP_200_OK
        assert returned_ids(response) == {match.id}

    def test_list_paginated_includes_unread_count_success(
        self, auth_client, admin_user, notification_factory
    ):
        notification_factory(user=admin_user, is_read=False)

        response = auth_client(admin_user).get(notifications_list_url())

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert response.data["unread_count"] == 1

    def test_create_method_not_allowed_fail(self, auth_client, admin_user):
        response = auth_client(admin_user).post(
            notifications_list_url(),
            {"title": "Nope", "description": "Nope", "type": "general"},
            format="json",
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert Notification.objects.count() == 0
