from decimal import Decimal

from apps.shared.constants import COMPANY_ROLES, STATION_ROLES
from apps.users.models import User


def set_balance(instance, amount):
    instance.balance = Decimal(amount)
    instance.save(update_fields=["balance"])


def cash_request_list_url():
    from django.urls import reverse

    return reverse("company-cash-requests-list")


def cash_request_detail_url(request_id):
    from django.urls import reverse

    return reverse("company-cash-requests-detail", kwargs={"pk": request_id})


def expected_amount(cash_request, user):
    if user.role in COMPANY_ROLES:
        return str(cash_request.company_cost)
    if user.role in STATION_ROLES:
        return str(cash_request.station_cost)
    return str(cash_request.amount)


def expected_is_owner(cash_request, user):
    if user.role == User.UserRoles.CompanyOwner:
        return True
    if user.role == User.UserRoles.CompanyBranchManager:
        return cash_request.created_by_id == user.id
    return False


def expected_driver_payload(driver):
    return {
        "id": driver.id,
        "name": driver.name,
        "phone_number": driver.phone_number,
        "branch": driver.branch_id,
        "code": driver.code,
    }


def expected_station_branch_payload(station_branch):
    if station_branch is None:
        return None
    return {
        "id": station_branch.id,
        "name": station_branch.name,
        "address": station_branch.address,
        "district": {
            "id": station_branch.district_id,
            "name": station_branch.district.name,
            "city": {"name": station_branch.district.city.name},
        },
        "station": station_branch.station_id,
    }


def expected_user_payload(user):
    if user is None:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "phone_number": user.phone_number,
        "role": user.role,
    }


def assert_cash_request_payload(data, cash_request, user):
    cash_request.refresh_from_db()
    driver = cash_request.driver
    approved_by = cash_request.approved_by
    assert data["id"] == cash_request.id
    assert data["code"] == cash_request.code
    assert data["otp"] == cash_request.otp
    assert data["driver"] == expected_driver_payload(driver)
    assert data["amount"] == expected_amount(cash_request, user)
    assert _as_decimal(data["company_cost"]) == _as_decimal(cash_request.company_cost)
    assert _as_decimal(data["station_cost"]) == _as_decimal(cash_request.station_cost)
    assert data["status"] == cash_request.status
    assert data["company"] == cash_request.company_id
    assert data["is_owner"] is expected_is_owner(cash_request, user)
    assert data["station_branch"] == expected_station_branch_payload(
        cash_request.station_branch
    )
    assert data["approved_by"] == expected_user_payload(approved_by)
    assert data["worker"] == data["approved_by"]
    assert data["created"]
    assert data["modified"]


def _as_decimal(value):
    if value is None:
        return None
    return Decimal(str(value))


def returned_ids(response):
    return {item["id"] for item in response.data["results"]}
