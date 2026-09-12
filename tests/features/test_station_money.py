"""The dashboard credits a station branch; the owner moves money station ↔ branch.

Each test follows the Given-When-Then template; the signed-in dashboard, owner,
manager and worker clients and the station/branch they act on live in ``setup``.
"""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import StationKhaznaTransaction
from apps.accounting.tests.api.v1.station_transaction.helpers import (
    create_payload,
    station_transaction_list_url,
)
from apps.auth.tests.helpers import profile_url
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification
from apps.stations.tests.helpers import home_url, notification_user_ids

from .helpers import fresh_balance, sign_in, station_branch_balance_url

pytestmark = [pytest.mark.django_db, pytest.mark.feature]

ZERO = Decimal("0.00")


def move(amount, direction):
    return {"amount": amount, "type": direction}


class TestStationMoney:
    @pytest.fixture(autouse=True)
    def setup(
        self, admin_user, station, branch, station_owner, branch_manager, station_worker
    ):
        self.station = station
        self.branch = branch
        self.manager_user = branch_manager
        self.admin = sign_in("dashboard", admin_user)
        self.owner = sign_in("station", station_owner)
        self.manager = sign_in("station", branch_manager)
        self.worker = sign_in("station", station_worker)
        self.balance_url = station_branch_balance_url(branch.id)

    def credit(self, client, amount, **overrides):
        payload = create_payload(
            self.station,
            self.branch,
            amount=amount,
            is_incoming=False,  # False adds to the balance
            status="approved",
        )
        payload.update(overrides)
        return client.post(station_transaction_list_url(), payload, format="json")

    def test_dashboard_credits_branch_and_owner_spreads_it_success(self):
        # Given the dashboard credits the branch by 500
        # When the owner moves money branch→station and back
        credited = self.credit(self.admin, "500.00")
        to_station = self.owner.post(
            self.balance_url, move("200.00", "subtract"), format="json"
        )
        back_to_branch = self.owner.post(
            self.balance_url, move("50.00", "add"), format="json"
        )
        home = self.owner.get(home_url())
        owner_profile = self.owner.get(profile_url())
        manager_profile = self.manager.get(profile_url())

        # Then the balances, home, profiles, khazna rows and notification agree
        assert credited.status_code == status.HTTP_201_CREATED, credited.data
        assert to_station.status_code == status.HTTP_200_OK, to_station.data
        assert back_to_branch.data == {"balance": Decimal("350.00")}
        assert fresh_balance(self.station) == Decimal("150.00")
        assert fresh_balance(self.branch) == Decimal("350.00")
        assert home.data["balance"] == Decimal("150.00")
        assert home.data["branches_balance"] == Decimal("350.00")
        assert home.data["total_balance"] == Decimal("500.00")
        assert owner_profile.data["balance"] == Decimal("150.00")
        assert manager_profile.data["balance"] == Decimal("350.00")
        assert StationKhaznaTransaction.objects.filter(is_internal=True).count() == 2
        assert self.manager_user.id in notification_user_ids(
            Notification.NotificationType.MONEY, title_contains="500"
        )

    @pytest.mark.parametrize("direction", ["subtract", "add"])
    def test_moves_without_enough_balance_fail(self, direction):
        # Given both balances are zero
        # When the owner tries to move money either direction
        response = self.owner.post(
            self.balance_url, move("10.00", direction), format="json"
        )

        # Then it is rejected and nothing moves
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_enough_balance"
        assert fresh_balance(self.station) == ZERO
        assert fresh_balance(self.branch) == ZERO

    def test_move_less_than_the_minimum_fail(self):
        # Given a funded station
        set_balance(self.station, "100.00")

        # When the owner moves less than the minimum transfer
        response = self.owner.post(self.balance_url, move("5.00", "add"), format="json")

        # Then it is rejected by validation and nothing moves
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "validation_error"
        assert fresh_balance(self.station) == Decimal("100.00")

    @pytest.mark.parametrize("actor", ["manager", "worker"])
    def test_only_the_owner_moves_station_money_fail(self, actor):
        # Given a funded station
        set_balance(self.station, "100.00")

        # When a non-owner station role tries to move money
        response = getattr(self, actor).post(
            self.balance_url, move("10.00", "add"), format="json"
        )

        # Then it is forbidden and nothing moves
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert fresh_balance(self.branch) == ZERO

    def test_credit_without_a_branch_crashes_fail(self):
        """Known bug: the create serializer indexes `attrs["station_branch"]`,
        so a station-level credit raises a KeyError (500)."""
        # Given a station-level credit payload with no branch
        payload = create_payload(self.station, self.branch, status="approved")
        payload.pop("station_branch")

        # When the dashboard posts it
        # Then the serializer raises a KeyError and nothing is credited
        with pytest.raises(KeyError):
            self.admin.post(station_transaction_list_url(), payload, format="json")

        assert fresh_balance(self.station) == ZERO

    def test_station_worker_can_approve_a_station_credit_success(self):
        """Open issue: every station role may create khazna transactions,
        including already-approved ones, so a worker can credit a branch."""
        # Given a signed-in station worker (from setup)
        # When they post an already-approved credit
        response = self.credit(self.worker, "5000.00")

        # Then the branch is credited without any dashboard review
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert fresh_balance(self.branch) == Decimal("5000.00")
