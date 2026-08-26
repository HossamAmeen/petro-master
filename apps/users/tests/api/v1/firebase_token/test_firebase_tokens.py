import pytest
from rest_framework import status

from apps.users.models import FirebaseToken
from apps.users.tests.helpers import (
    firebase_tokens_delete_by_token_url,
    firebase_tokens_detail_url,
    firebase_tokens_list_url,
)


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_create_without_authentication_fail(api_client):
    response = api_client.post(
        firebase_tokens_list_url(),
        {"token": "fcm-unauthenticated"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert FirebaseToken.objects.count() == 0


def test_create_success(auth_client, company_owner, company):
    response = auth_client(company_owner, company_id=company.id).post(
        firebase_tokens_list_url(),
        {"token": "fcm-company-owner"},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = FirebaseToken.objects.get(token="fcm-company-owner")
    assert created.user_id == company_owner.id
    assert response.data["token"] == "fcm-company-owner"
    assert "id" in response.data
    assert "created" in response.data


def test_create_missing_token_fail(auth_client, admin_user):
    response = auth_client(admin_user).post(
        firebase_tokens_list_url(),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert FirebaseToken.objects.count() == 0


def test_create_duplicate_token_fail(auth_client, admin_user, firebase_token_factory):
    existing = firebase_token_factory(admin_user, token="fcm-duplicate")

    response = auth_client(admin_user).post(
        firebase_tokens_list_url(),
        {"token": existing.token},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert FirebaseToken.objects.filter(token="fcm-duplicate").count() == 1


def test_list_method_not_allowed_fail(auth_client, admin_user):
    response = auth_client(admin_user).get(firebase_tokens_list_url())

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_delete_by_pk_success(auth_client, admin_user, firebase_token_factory):
    token = firebase_token_factory(admin_user)

    response = auth_client(admin_user).delete(firebase_tokens_detail_url(token.id))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not FirebaseToken.objects.filter(pk=token.id).exists()


def test_delete_other_users_token_fail(
    auth_client, admin_user, company_owner, firebase_token_factory
):
    token = firebase_token_factory(company_owner)

    response = auth_client(admin_user).delete(firebase_tokens_detail_url(token.id))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert FirebaseToken.objects.filter(pk=token.id).exists()


def test_delete_by_token_success(auth_client, station_worker, station, firebase_token_factory):
    token = firebase_token_factory(station_worker, token="fcm-to-delete")

    response = auth_client(station_worker, station_id=station.id).delete(
        firebase_tokens_delete_by_token_url(),
        {"token": "fcm-to-delete"},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not FirebaseToken.objects.filter(pk=token.id).exists()


def test_delete_by_token_missing_body_fail(auth_client, admin_user):
    response = auth_client(admin_user).delete(
        firebase_tokens_delete_by_token_url(),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"] == "Token string is required in the request body."


def test_delete_by_token_unknown_fail(auth_client, admin_user):
    response = auth_client(admin_user).delete(
        firebase_tokens_delete_by_token_url(),
        {"token": "missing-fcm"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data["error"] == "Firebase token not found for this user."


def test_delete_by_token_does_not_remove_other_users_token_fail(
    auth_client, admin_user, company_owner, firebase_token_factory
):
    token = firebase_token_factory(company_owner, token="shared-looking-token")

    response = auth_client(admin_user).delete(
        firebase_tokens_delete_by_token_url(),
        {"token": "shared-looking-token"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert FirebaseToken.objects.filter(pk=token.id).exists()
