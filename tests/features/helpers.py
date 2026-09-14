"""Steps shared by the feature tests: real logins and multi-request flows."""

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.auth.tests.helpers import LOGIN_PASSWORD, login_payload, set_login_password
from apps.companies.models.company_models import Car
from apps.companies.tests.api.v1.car.helpers import verify_url
from apps.stations.tests.helpers import gas_url, image_file, other_url

ALL_DAYS = list(Car.FuelAllowedDay.values)

LOGIN_URL_NAMES = {
    "company": "company_login",
    "station": "station_login",
    "dashboard": "dashboard_login",
}


def login(kind, user, password=LOGIN_PASSWORD):
    """POST to the real login endpoint and return its response."""
    return APIClient().post(
        reverse(LOGIN_URL_NAMES[kind]),
        login_payload(user, password=password),
        format="json",
    )


def bearer_client(access_token):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client


def login_client(kind, user, password=LOGIN_PASSWORD):
    """Return a client carrying the access token the real login issued."""
    response = login(kind, user, password)
    require(response, status.HTTP_200_OK, f"{kind} login for {user.phone_number}")
    return bearer_client(response.data["access"])


def sign_in(kind, user):
    """Log in a fixture user. Fixtures store raw passwords, so hash one first."""
    set_login_password(user)
    return login_client(kind, user)


def require(response, expected_status, step):
    """Stop a flow at the step that broke instead of failing later on a balance."""
    if response.status_code != expected_status:
        raise RuntimeError(f"{step} returned {response.status_code}: {response.data}")
    return response


def verify(client, driver, car, service_type="petrol"):
    return client.post(verify_url(driver.code, car.code, service_type))


def start_pump(client, operation_id):
    return client.patch(
        gas_url(operation_id),
        {"start_time": timezone.localtime().isoformat()},
        format="json",
    )


def read_meter(client, operation_id, meter):
    return client.patch(
        gas_url(operation_id),
        {"car_meter": meter, "motor_image": image_file("motor.png")},
        format="multipart",
    )


def pump(client, operation_id, amount):
    return client.patch(
        gas_url(operation_id),
        {"amount": amount, "fuel_image": image_file("fuel.png")},
        format="multipart",
    )


def start_fueling(client, driver, car, *, meter):
    """Verify, start the pump and read the meter; return the operation id."""
    response = require(verify(client, driver, car), status.HTTP_200_OK, "verify")
    operation_id = response.data["operation_id"]
    require(start_pump(client, operation_id), status.HTTP_200_OK, "start_time")
    require(read_meter(client, operation_id, meter), status.HTTP_200_OK, "car_meter")
    return operation_id


def fuel(client, driver, car, *, amount, meter):
    """Run the worker's four fueling requests; return the operation id and the
    response of the last (amount) request."""
    operation_id = start_fueling(client, driver, car, meter=meter)
    return operation_id, pump(client, operation_id, amount)


def complete_other_service(client, driver, car, *, service, cost):
    """Verify a non-petrol visit and complete it; return the operation id and
    the completing response."""
    response = require(
        verify(client, driver, car, "other"), status.HTTP_200_OK, "verify"
    )
    operation_id = response.data["operation_id"]
    response = client.patch(
        other_url(operation_id),
        {"service": service.id, "cost": cost, "car_image": image_file("car.png")},
        format="multipart",
    )
    return operation_id, response


def fresh_balance(instance):
    instance.refresh_from_db(fields=["balance"])
    return instance.balance


def company_home_url():
    return reverse("company-home")


def company_branch_detail_url(branch_id):
    return reverse("company-branches-detail", kwargs={"pk": branch_id})


def company_branch_balance_url(branch_id):
    return reverse("company-branches-update_balance", kwargs={"pk": branch_id})


def assign_company_managers_url(branch_id):
    return reverse("company-branches-assign-managers", kwargs={"pk": branch_id})


def station_branch_balance_url(branch_id):
    return reverse("station-branches-update-balance", kwargs={"pk": branch_id})


def station_branch_action_url(action, branch_id):
    return reverse(f"station-branches-{action}", kwargs={"pk": branch_id})
