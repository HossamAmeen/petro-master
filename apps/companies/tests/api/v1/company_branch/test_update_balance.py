from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.notifications.models import Notification


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def update_balance_url(branch_id):
    return reverse("company-branches-update_balance", kwargs={"pk": branch_id})


def set_balance(instance, amount):
    instance.balance = Decimal(amount)
    instance.save(update_fields=["balance"])


def test_update_balance_without_authentication_fail(api_client, company_branch):
    response = api_client.post(
        update_balance_url(company_branch.id),
        {"amount": "10.00", "type": "add"},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize(
    "role_fixture",
    ["admin_user", "company_branch_manager", "station_worker"],
)
def test_update_balance_forbidden_role_fail(
    role_fixture,
    request,
    auth_client,
    company,
    station,
    company_branch,
):
    user = request.getfixturevalue(role_fixture)
    client_kwargs = {}
    if role_fixture == "company_branch_manager":
        client_kwargs["company_id"] = company.id
    if role_fixture == "station_worker":
        client_kwargs["station_id"] = station.id

    response = auth_client(user, **client_kwargs).post(
        update_balance_url(company_branch.id),
        {"amount": "10.00", "type": "add"},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_add_balance_as_company_owner_success(
    auth_client,
    company_owner,
    company,
    company_branch,
    company_branch_manager,
):
    set_balance(company, "100.00")

    response = auth_client(company_owner, company_id=company.id).post(
        update_balance_url(company_branch.id),
        {"amount": "40.00", "type": "add"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    company.refresh_from_db()
    company_branch.refresh_from_db()
    assert company.balance == Decimal("60.00")
    assert company_branch.balance == Decimal("40.00")
    assert response.data["balance"] == Decimal("40.00")
    assert CompanyKhaznaTransaction.objects.filter(
        company_id=company.id,
        company_branch_id=company_branch.id,
        amount=Decimal("40.00"),
        is_internal=True,
        for_what=CompanyKhaznaTransaction.ForWhat.CAR,
        status=CompanyKhaznaTransaction.TransactionStatus.APPROVED,
    ).exists()
    notified = set(
        Notification.objects.filter(type=Notification.NotificationType.MONEY).values_list(
            "user_id", flat=True
        )
    )
    assert notified == {company_owner.id, company_branch_manager.id}


def test_subtract_balance_as_company_owner_success(
    auth_client,
    company_owner,
    company,
    company_branch,
):
    set_balance(company, "20.00")
    set_balance(company_branch, "50.00")

    response = auth_client(company_owner, company_id=company.id).post(
        update_balance_url(company_branch.id),
        {"amount": "15.00", "type": "subtract"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data
    company.refresh_from_db()
    company_branch.refresh_from_db()
    assert company.balance == Decimal("35.00")
    assert company_branch.balance == Decimal("35.00")
    assert Notification.objects.filter(
        user_id=company_owner.id, type=Notification.NotificationType.MONEY
    ).exists()


def test_add_balance_insufficient_company_balance_fail(
    auth_client, company_owner, company, company_branch
):
    set_balance(company, "10.00")

    response = auth_client(company_owner, company_id=company.id).post(
        update_balance_url(company_branch.id),
        {"amount": "10.01", "type": "add"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_enough_balance"
    company.refresh_from_db()
    company_branch.refresh_from_db()
    assert company.balance == Decimal("10.00")
    assert company_branch.balance == Decimal("0.00")
    assert CompanyKhaznaTransaction.objects.count() == 0


def test_subtract_balance_insufficient_branch_balance_fail(
    auth_client, company_owner, company, company_branch
):
    set_balance(company_branch, "10.00")

    response = auth_client(company_owner, company_id=company.id).post(
        update_balance_url(company_branch.id),
        {"amount": "10.01", "type": "subtract"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == "not_enough_balance"
    company_branch.refresh_from_db()
    assert company_branch.balance == Decimal("10.00")


def test_update_balance_other_company_branch_fail(
    auth_client, company_owner, company, other_company_branch
):
    response = auth_client(company_owner, company_id=company.id).post(
        update_balance_url(other_company_branch.id),
        {"amount": "10.00", "type": "add"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": "0.99", "type": "add"},
        {"amount": "-1.00", "type": "add"},
        {"amount": "1.00", "type": "invalid"},
        {"type": "add"},
        {"amount": "1.00"},
    ],
)
def test_update_balance_invalid_payload_fail(
    payload, auth_client, company_owner, company, company_branch
):
    response = auth_client(company_owner, company_id=company.id).post(
        update_balance_url(company_branch.id),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    company.refresh_from_db()
    company_branch.refresh_from_db()
    assert company.balance == Decimal("0.00")
    assert company_branch.balance == Decimal("0.00")
