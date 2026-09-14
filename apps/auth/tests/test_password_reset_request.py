from unittest.mock import patch

import pytest
from django.core import mail
from rest_framework import status

from apps.auth.tests.helpers import (
    password_reset_request_url,
    set_login_password,
)
from apps.companies.factories import UserFactory
from apps.users.models import User

pytestmark = [pytest.mark.api, pytest.mark.django_db]


class TestPasswordResetRequest:

    def test_password_reset_request_sends_email_for_active_user_success(
        self, api_client
    ):
        user = UserFactory()

        response = api_client.post(
            password_reset_request_url(),
            {"email": user.email},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"message": "Password reset request sent successfully"}
        user.refresh_from_db()
        assert user.reset_password_token
        assert user.reset_password_token_created_at is not None
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.subject == "Password Reset Request"
        assert sent.to == [user.email]
        html_body = sent.alternatives[0][0]
        assert user.reset_password_token in html_body
        assert "password-reset-confirm" in html_body

    def test_password_reset_request_queues_email_with_celery_success(
        self, api_client, settings, django_capture_on_commit_callbacks
    ):
        settings.USE_CELERY = True
        user = UserFactory()

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            response = api_client.post(
                password_reset_request_url(),
                {"email": user.email},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert len(callbacks) == 1
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]

    def test_password_reset_request_unknown_email_fail(self, api_client):
        response = api_client.post(
            password_reset_request_url(),
            {"email": "missing@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == "user_not_found"
        assert response.data["message"] == "لاي يوجد مستخدم, الرجاء التواصل مع المسؤول."
        assert mail.outbox == []

    def test_password_reset_request_inactive_user_fail(self, api_client):
        user = UserFactory(is_active=False)

        response = api_client.post(
            password_reset_request_url(),
            {"email": user.email},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["code"] == "user_not_found"
        user.refresh_from_db()
        assert user.reset_password_token is None
        assert mail.outbox == []

    def test_password_reset_request_invalid_email_fail(self, api_client):
        response = api_client.post(
            password_reset_request_url(),
            {"email": "not-an-email"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "validation_error"
        assert mail.outbox == []

    def test_password_reset_request_missing_email_fail(self, api_client):
        response = api_client.post(password_reset_request_url(), {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "validation_error"

    def test_password_reset_request_send_mail_failure_fail(self, api_client):
        user = UserFactory()

        with patch(
            "apps.auth.tasks.send_mail",
            side_effect=Exception("smtp down"),
        ):
            response = api_client.post(
                password_reset_request_url(),
                {"email": user.email},
                format="json",
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["code"] == "failed_to_send_password_reset_request"
        assert response.data["message"] == "Failed to send password reset request"
        assert "smtp down" in response.data["errors"]
        user.refresh_from_db()
        assert user.reset_password_token
        assert mail.outbox == []

    def test_password_reset_request_replaces_existing_token_success(self, api_client):
        user = UserFactory()
        first_token = user.create_password_reset_token()

        response = api_client.post(
            password_reset_request_url(),
            {"email": user.email},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.reset_password_token
        assert user.reset_password_token != first_token

    def test_password_reset_request_get_method_fail(self, api_client):
        response = api_client.get(password_reset_request_url())

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_password_reset_request_company_owner_success(
        self, api_client, company_owner
    ):
        set_login_password(company_owner)

        response = api_client.post(
            password_reset_request_url(),
            {"email": company_owner.email},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        company_owner.refresh_from_db()
        assert company_owner.reset_password_token
        assert User.objects.get(pk=company_owner.pk).reset_password_token
