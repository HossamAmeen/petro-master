from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from apps.companies.models.company_models import Car, Driver
from apps.utilities.testing import assert_soft_deleted

DELETED_TARGETS = [("car",), ("driver",), ("car", "driver")]


def set_balance(instance, amount):
    instance.balance = Decimal(amount)
    instance.save(update_fields=["balance"])


def soft_delete_car_or_driver(owner_client, operation, targets):
    """Soft-delete the operation's `targets` ("car", "driver") through the API."""
    rows = {
        "car": (Car, operation.car_id, "cars-detail"),
        "driver": (Driver, operation.driver_id, "drivers-detail"),
    }
    for target in targets:
        model, pk, route = rows[target]
        response = owner_client.delete(reverse(route, kwargs={"pk": pk}))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert_soft_deleted(model, pk)
