from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.companies.models.company_models import Car
from apps.companies.tests.helpers import set_balance  # noqa: F401  (re-exported)
from apps.notifications.models import Notification


def fund_balance_source(car, company_branch, company, balance_source, **overrides):
    """Point the car at a holder and leave only that holder funded."""
    car.balance_source = balance_source
    car.balance = Decimal(overrides.get("car_balance", "0.00"))
    car.save(update_fields=["balance_source", "balance"])
    set_balance(company_branch, "0.00")
    set_balance(company, "0.00")
    holder = company_branch if balance_source == Car.BalanceSource.BRANCH else company
    set_balance(holder, overrides.get("holder_balance", "1000.00"))
    return holder


def image_file(name="photo.png"):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def worker_client(auth_client, station_worker, station):
    return auth_client(station_worker, station_id=station.id)


def gas_url(pk):
    return reverse("station-gas-operations", kwargs={"pk": pk})


def other_url(pk):
    return reverse("station-other-operations", kwargs={"pk": pk})


def stations_list_url(**params):
    url = reverse("stations-list")
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"
    return url


def stations_detail_url(pk):
    return reverse("stations-detail", kwargs={"pk": pk})


def branches_list_url(**params):
    url = reverse("station-branches-list")
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"
    return url


def branches_detail_url(pk):
    return reverse("station-branches-detail", kwargs={"pk": pk})


def services_list_url(**params):
    url = reverse("services-list")
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"
    return url


def services_detail_url(pk):
    return reverse("services-detail", kwargs={"pk": pk})


def home_url():
    return reverse("station-home")


def operations_url(**params):
    url = reverse("station-operations")
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"
    return url


def reports_url(**params):
    url = reverse("station-reports")
    if params:
        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{url}?{query}"
    return url


def returned_ids(response):
    payload = response.data
    if isinstance(payload, dict) and "results" in payload:
        return {item["id"] for item in payload["results"]}
    return {item["id"] for item in payload}


def gas_costs(amount, service, company_branch, station_branch):
    amount = Decimal(amount)
    service_cost = Decimal(str(service.cost))
    company_liter_cost = (
        service_cost * (Decimal(str(company_branch.fees)) / Decimal("100"))
        + service_cost
    )
    cost = round(amount * service_cost, 2)
    company_cost = round(amount * company_liter_cost, 2)
    station_cost = round(
        amount * (service_cost + Decimal(str(station_branch.fees))),
        2,
    )
    profits = round(company_cost - station_cost, 2)
    return {
        "cost": cost,
        "company_cost": company_cost,
        "station_cost": station_cost,
        "profits": profits,
        "company_liter_cost": company_liter_cost,
    }


def other_costs(cost, company_branch, station_branch):
    cost = Decimal(cost)
    company_cost = (
        cost * Decimal(str(company_branch.other_service_fees)) / Decimal("100")
    ) + cost
    station_cost = cost - (
        cost * Decimal(str(station_branch.other_service_fees)) / Decimal("100")
    )
    return {"company_cost": company_cost, "station_cost": station_cost}


def prepare_gas_for_amount(operation, meter="10100"):
    operation.start_time = timezone.localtime()
    operation.car_meter = Decimal(meter)
    operation.save(update_fields=["start_time", "car_meter"])
    return operation


def notification_user_ids(notification_type=None, title_contains=None):
    queryset = Notification.objects.all()
    if notification_type is not None:
        queryset = queryset.filter(type=notification_type)
    if title_contains is not None:
        queryset = queryset.filter(title__contains=title_contains)
    return set(queryset.values_list("user_id", flat=True))


def notification_titles_for(user_id):
    return list(
        Notification.objects.filter(user_id=user_id)
        .order_by("id")
        .values_list("title", "type")
    )
