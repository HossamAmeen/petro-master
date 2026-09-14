from datetime import date, datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.utils import timezone

from apps.shared.helpers import today


class TestToday:

    def test_returns_current_date_success(self):
        fixed_now = datetime(2026, 3, 10, 9, 0, tzinfo=dt_timezone.utc)

        with patch("apps.shared.helpers.timezone.now", return_value=fixed_now):
            assert today() == date(2026, 3, 10)

    def test_returns_utc_date_not_local_date_late_in_the_day_success(self):
        """Documents actual (buggy) behavior: `today()` takes the date of the UTC
        timestamp. From 21:00 UTC (midnight in Africa/Cairo) it still returns the
        previous day, so `created__date=today()` filters, which compare in local
        time, miss everything created that local day."""
        late_utc = datetime(2026, 3, 10, 22, 30, tzinfo=dt_timezone.utc)

        with patch("apps.shared.helpers.timezone.now", return_value=late_utc):
            assert today() == date(2026, 3, 10)
            assert timezone.localtime(late_utc).date() == date(2026, 3, 11)
