from decimal import Decimal

import pytest
from rest_framework import status

from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.models.company_models import Company, CompanyBranch
from apps.companies.tests.api.v1.cash_request.helpers import (
    cash_request_list_url,
    set_balance,
)
from apps.notifications.models import Notification


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_create_without_authentication_fail(
    api_client, cash_request_payload_factory
):
    response = api_client.post(
        cash_request_list_url(),
        cash_request_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert CompanyCashRequest.objects.count() == 0


@pytest.mark.parametrize("role_fixture", ["station_worker", "station_owner"])
def test_create_station_role_fail(
    role_fixture,
    request,
    auth_client,
    station,
    cash_request_payload_factory,
):
    user = request.getfixturevalue(role_fixture)

    response = auth_client(user, station_id=station.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert CompanyCashRequest.objects.count() == 0


def test_create_as_company_owner_success(
    auth_client,
    company_owner,
    company,
    company_branch,
    company_driver,
    cash_request_payload_factory,
    mock_cash_request_sms,
):
    company_branch.cash_request_fees = Decimal("10.00")
    company_branch.save(update_fields=["cash_request_fees"])
    set_balance(company, "200.00")
    payload = cash_request_payload_factory(amount="100.00")

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data == {
        "driver": company_driver.id,
        "amount": "100.00",
    }
    created = CompanyCashRequest.objects.get()
    company.refresh_from_db()
    assert created.driver_id == company_driver.id
    assert created.company_id == company.id
    assert created.amount == Decimal("100.00")
    assert created.company_cost == Decimal("110.00")
    assert created.station_cost is None
    assert created.status == CompanyCashRequest.Status.IN_PROGRESS
    assert created.station_id is None
    assert created.station_branch_id is None
    assert created.approved_by_id is None
    assert created.created_by_id == company_owner.id
    assert created.code
    assert created.otp
    assert len(created.otp) == 6
    assert company.balance == Decimal("90.00")
    notification = Notification.objects.get(
        user_id=company_owner.id, type=Notification.NotificationType.GENERAL
    )
    assert company_driver.name in notification.title
    assert created.otp in notification.title
    assert company_driver.name in notification.description
    assert created.otp in notification.description
    mock_cash_request_sms.assert_called_once()
    sms_message, sms_phone = mock_cash_request_sms.call_args.args
    assert sms_phone == company_driver.phone_number
    assert created.otp in sms_message
    assert str(created.amount) in sms_message


def test_create_as_branch_manager_deducts_branch_balance_success(
    auth_client,
    company_branch_manager,
    company,
    company_branch,
    company_driver,
    cash_request_payload_factory,
):
    company_branch.cash_request_fees = Decimal("10.00")
    company_branch.save(update_fields=["cash_request_fees"])
    set_balance(company, "200.00")
    set_balance(company_branch, "200.00")

    response = auth_client(company_branch_manager, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="100.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["driver"] == company_driver.id
    assert response.data["amount"] == "100.00"
    created = CompanyCashRequest.objects.get()
    company.refresh_from_db()
    company_branch.refresh_from_db()
    assert created.created_by_id == company_branch_manager.id
    assert created.company_id == company.id
    assert created.company_cost == Decimal("110.00")
    assert company.balance == Decimal("200.00")
    assert company_branch.balance == Decimal("90.00")
    assert not Notification.objects.filter(
        type=Notification.NotificationType.GENERAL
    ).exists()


@pytest.mark.parametrize("role_fixture", ["admin_user", "finance_user", "customer_support_user"])
def test_create_as_dashboard_deducts_branch_balance_success(
    role_fixture,
    request,
    auth_client,
    company,
    company_branch,
    company_driver,
    cash_request_payload_factory,
):
    user = request.getfixturevalue(role_fixture)
    company_branch.cash_request_fees = Decimal("10.00")
    company_branch.save(update_fields=["cash_request_fees"])
    set_balance(company, "200.00")
    set_balance(company_branch, "200.00")

    response = auth_client(user, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="100.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data == {
        "driver": company_driver.id,
        "amount": "100.00",
    }
    created = CompanyCashRequest.objects.get()
    company.refresh_from_db()
    company_branch.refresh_from_db()
    assert created.created_by_id == user.id
    assert created.company_id == company.id
    assert created.company_cost == Decimal("110.00")
    assert created.status == CompanyCashRequest.Status.IN_PROGRESS
    assert company.balance == Decimal("200.00")
    assert company_branch.balance == Decimal("90.00")


def test_create_duplicate_in_progress_for_driver_fail(
    auth_client,
    company_owner,
    company,
    company_driver,
    cash_request_factory,
    cash_request_payload_factory,
):
    set_balance(company, "200.00")
    cash_request_factory(company=company, driver=company_driver)

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="50.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["message"] == "السائق لديه طلب بالفعل"
    assert CompanyCashRequest.objects.count() == 1
    company.refresh_from_db()
    assert company.balance == Decimal("200.00")


def test_create_after_previous_request_completed_success(
    auth_client,
    company_owner,
    company,
    company_driver,
    cash_request_factory,
    cash_request_payload_factory,
):
    set_balance(company, "200.00")
    cash_request_factory(
        company=company,
        driver=company_driver,
        status=CompanyCashRequest.Status.APPROVED,
        station_cost=Decimal("50.00"),
    )

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="40.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert CompanyCashRequest.objects.count() == 2
    created = CompanyCashRequest.objects.get(amount=Decimal("40.00"))
    assert created.status == CompanyCashRequest.Status.IN_PROGRESS
    company.refresh_from_db()
    assert company.balance == Decimal("160.00")


def test_create_other_company_driver_fail(
    auth_client,
    company_owner,
    company,
    driver_factory,
    other_company_branch,
    cash_request_payload_factory,
):
    set_balance(company, "200.00")
    other_driver = driver_factory(branch=other_company_branch)

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(driver=other_driver.id, amount="50.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CompanyCashRequest.objects.count() == 0


def test_create_unmanaged_driver_as_branch_manager_fail(
    auth_client,
    company_branch_manager,
    company,
    second_company_branch,
    driver_factory,
    cash_request_payload_factory,
):
    set_balance(company, "200.00")
    unmanaged = driver_factory(branch=second_company_branch)

    response = auth_client(company_branch_manager, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(driver=unmanaged.id, amount="50.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CompanyCashRequest.objects.count() == 0


def test_create_insufficient_company_balance_fail(
    auth_client,
    company_owner,
    company,
    cash_request_payload_factory,
):
    set_balance(company, "49.99")

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="50.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CompanyCashRequest.objects.count() == 0
    company.refresh_from_db()
    assert company.balance == Decimal("49.99")


def test_create_insufficient_branch_balance_as_manager_fail(
    auth_client,
    company_branch_manager,
    company,
    company_branch,
    cash_request_payload_factory,
):
    set_balance(company, "200.00")
    set_balance(company_branch, "10.00")

    response = auth_client(company_branch_manager, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="50.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CompanyCashRequest.objects.count() == 0
    company_branch.refresh_from_db()
    assert company_branch.balance == Decimal("10.00")


def test_create_amount_equal_to_balance_success(
    auth_client,
    company_owner,
    company,
    company_driver,
    cash_request_payload_factory,
):
    set_balance(company, "50.00")

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="50.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyCashRequest.objects.get()
    company.refresh_from_db()
    assert created.amount == Decimal("50.00")
    assert created.company_cost == Decimal("50.00")
    assert created.driver_id == company_driver.id
    assert company.balance == Decimal("0.00")


def test_create_fees_push_cost_over_balance_success(
    auth_client,
    company_owner,
    company,
    company_branch,
    cash_request_payload_factory,
):
    company_branch.cash_request_fees = Decimal("10.00")
    company_branch.save(update_fields=["cash_request_fees"])
    set_balance(company, "105.00")

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        cash_request_payload_factory(amount="100.00"),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED, response.data
    created = CompanyCashRequest.objects.get()
    company.refresh_from_db()
    assert created.company_cost == Decimal("110.00")
    assert company.balance == Decimal("-5.00")


@pytest.mark.parametrize(
    "payload",
    [
        {"amount": "50.00"},
        {"driver": 1},
        {"driver": 1, "amount": "0.50"},
        {"driver": 1, "amount": "-1.00"},
        {"driver": 999_999, "amount": "50.00"},
    ],
)
def test_create_invalid_payload_fail(
    payload,
    auth_client,
    company_owner,
    company,
    company_driver,
):
    set_balance(company, "200.00")
    if payload.get("driver") == 1:
        payload = {**payload, "driver": company_driver.id}

    response = auth_client(company_owner, company_id=company.id).post(
        cash_request_list_url(),
        payload,
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert CompanyCashRequest.objects.count() == 0
    assert Company.objects.get(pk=company.id).balance == Decimal("200.00")
    assert CompanyBranch.objects.get(pk=company_driver.branch_id).balance == Decimal(
        "0.00"
    )
