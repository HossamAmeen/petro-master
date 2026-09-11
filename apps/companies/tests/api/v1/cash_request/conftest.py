from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.users.models import User, Worker


@pytest.fixture(autouse=True)
def mock_cash_request_sms():
    with patch("apps.notifications.tasks.send_sms") as send_sms:
        yield send_sms


@pytest.fixture
def worker_factory(db, admin_user, branch):
    counter = {"n": 0}

    def create_worker(**overrides):
        counter["n"] += 1
        token = uuid4().hex
        defaults = {
            "name": f"Worker {counter['n']}",
            "phone_number": f"017{token[:8]}",
            "email": f"worker-{token[:10]}@example.com",
            "password": "password123",
            "role": User.UserRoles.StationWorker,
            "station_branch": branch,
            "created_by": admin_user,
        }
        defaults.update(overrides)
        return Worker.objects.create(**defaults)

    return create_worker
