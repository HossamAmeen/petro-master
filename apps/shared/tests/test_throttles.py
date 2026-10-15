from unittest.mock import patch

import pytest
from django.core.cache import cache
from rest_framework import status

from apps.auth.tests.helpers import (
    company_login_url,
    dashboard_login_url,
    station_login_url,
)
from apps.shared.throttles import LoginRateThrottle

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestLoginRateThrottle:
    @pytest.fixture(autouse=True)
    def setup(self):
        cache.clear()
        with patch.object(LoginRateThrottle, "THROTTLE_RATES", {"login": "3/min"}):
            yield
        cache.clear()

    @pytest.mark.parametrize(
        "url_builder", [dashboard_login_url, company_login_url, station_login_url]
    )
    def test_repeated_failed_logins_are_throttled_fail(self, api_client, url_builder):
        payload = {"identifier": "01000000000", "password": "wrong"}

        statuses = [
            api_client.post(url_builder(), payload, format="json").status_code
            for _ in range(5)
        ]

        assert statuses[:3] == [status.HTTP_401_UNAUTHORIZED] * 3
        assert statuses[3:] == [status.HTTP_429_TOO_MANY_REQUESTS] * 2

    def test_other_client_ip_is_not_throttled_success(self, api_client):
        payload = {"identifier": "01000000000", "password": "wrong"}
        for _ in range(4):
            api_client.post(dashboard_login_url(), payload, format="json")

        response = api_client.post(
            dashboard_login_url(),
            payload,
            format="json",
            REMOTE_ADDR="10.9.9.9",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
