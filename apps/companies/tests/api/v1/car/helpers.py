from django.urls import reverse


def car_list_url():
    return reverse("cars-list")


def car_detail_url(car_id):
    return reverse("cars-detail", kwargs={"pk": car_id})


def update_balance_url(car_id):
    return reverse("cars-update_balance", kwargs={"pk": car_id})


def verify_url(driver_code, car_code, service_type="petrol"):
    return reverse(
        "verify-driver",
        kwargs={
            "driver_code": driver_code,
            "car_code": car_code,
            "service_type": service_type,
        },
    )
