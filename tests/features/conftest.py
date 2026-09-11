from decimal import Decimal
from unittest.mock import patch

import pytest

from .helpers import ALL_DAYS


@pytest.fixture(autouse=True)
def mock_sms():
    """Cash-request OTPs go out by SMS; never reach the provider."""
    with patch("apps.companies.helper.send_sms") as send_sms:
        yield send_sms


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Meter/fuel/car images and Excel exports are written to a temp dir."""
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def local_cache(settings):
    """The project keeps its cache and sessions in redis, which tests can't reach."""
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.db"
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }


@pytest.fixture
def fees(company_branch, branch):
    """The company pays 10% on top of fuel and other services and 5% on cash
    requests; the station branch keeps 0.50 per litre, 5% and 2%."""
    company_branch.fees = Decimal("10.00")
    company_branch.other_service_fees = Decimal("10.00")
    company_branch.cash_request_fees = Decimal("5.00")
    company_branch.save(
        update_fields=["fees", "other_service_fees", "cash_request_fees"]
    )
    branch.fees = Decimal("0.50")
    branch.other_service_fees = Decimal("5.00")
    branch.cash_request_fees = Decimal("2.00")
    branch.save(update_fields=["fees", "other_service_fees", "cash_request_fees"])


@pytest.fixture
def fuelable_car(car_factory):
    """Petrol car allowed every day: 40 L permitted per fill, meter at 10000."""
    return car_factory(fuel_allowed_days=ALL_DAYS, last_meter=10000)
