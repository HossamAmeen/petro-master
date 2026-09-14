from decimal import Decimal

import pytest

from apps.accounting.models import KhaznaTransaction, StationKhaznaTransaction


@pytest.fixture
def khazna_transaction_factory(db, admin_user):
    counter = {"n": 0}

    def create_transaction(**overrides):
        counter["n"] += 1
        defaults = {
            "amount": Decimal("10.00"),
            "is_incoming": True,
            "status": KhaznaTransaction.TransactionStatus.PENDING,
            "reference_code": f"BASEREF{counter['n']:05d}",
            "created_by": admin_user,
        }
        defaults.update(overrides)
        return KhaznaTransaction.objects.create(**defaults)

    return create_transaction


@pytest.fixture
def station_transaction_factory(db, admin_user, station, branch):
    counter = {"n": 0}

    def create_transaction(**overrides):
        counter["n"] += 1
        defaults = {
            "station": station,
            "station_branch": branch,
            "amount": Decimal("10.00"),
            "is_incoming": True,
            "status": StationKhaznaTransaction.TransactionStatus.APPROVED,
            "reference_code": f"STREF{counter['n']:05d}",
            "created_by": admin_user,
            "updated_by": admin_user,
        }
        defaults.update(overrides)
        return StationKhaznaTransaction.objects.create(**defaults)

    return create_transaction
