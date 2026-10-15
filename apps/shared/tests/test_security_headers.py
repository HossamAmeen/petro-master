import pytest
from django.test import override_settings
from rest_framework import status

pytestmark = [pytest.mark.api, pytest.mark.django_db]

URL = "/api/v1/geo/cities/"


class TestHstsHeader:
    @override_settings(SECURE_HSTS_SECONDS=31536000)
    def test_hsts_header_sent_on_https_request_success(self, api_client):
        response = api_client.get(URL, secure=True)

        assert response.status_code == status.HTTP_200_OK
        assert response["Strict-Transport-Security"] == "max-age=31536000"

    @override_settings(
        SECURE_HSTS_SECONDS=31536000,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    )
    def test_hsts_header_sent_behind_tls_proxy_success(self, api_client):
        response = api_client.get(URL, HTTP_X_FORWARDED_PROTO="https")

        assert response["Strict-Transport-Security"] == "max-age=31536000"

    def test_hsts_header_off_by_default_success(self, api_client):
        response = api_client.get(URL, secure=True)

        assert "Strict-Transport-Security" not in response
