"""A company sends a driver cash; a station worker hands it over with the OTP.

Each test follows the Given-When-Then template; the funded company/branch/station,
the driver and the signed-in owner/manager/worker clients live in ``setup``.
"""

from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.company_cash_models import CompanyCashRequest
from apps.companies.tests.api.v1.cash_request.helpers import (
    cash_request_detail_url,
    cash_request_list_url,
)
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification
from apps.stations.tests.helpers import notification_user_ids, reports_url

from .helpers import fresh_balance, sign_in

pytestmark = [pytest.mark.django_db, pytest.mark.feature]


def ids(response):
    return [item["id"] for item in response.data["results"]]


class TestCashRequest:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        fees,
        company,
        company_owner,
        company_branch,
        company_branch_manager,
        company_driver,
        branch,
        station_owner,
        branch_manager,
        station_worker,
    ):
        self.company = company
        self.company_branch = company_branch
        self.station_branch = branch
        self.driver = company_driver
        self.users = {
            "company_owner": company_owner,
            "company_manager": company_branch_manager,
            "station_owner": station_owner,
            "station_manager": branch_manager,
            "worker": station_worker,
        }
        set_balance(company, "1000.00")
        set_balance(company_branch, "1000.00")
        set_balance(branch, "500.00")
        self.owner = sign_in("company", company_owner)
        self.manager = sign_in("company", company_branch_manager)
        self.worker = sign_in("station", station_worker)

    def request_cash(self, client=None, amount="100.00"):
        return (client or self.owner).post(
            cash_request_list_url(),
            {"driver": self.driver.id, "amount": amount},
            format="json",
        )

    def hand_over(self, cash_request, otp=None):
        return self.worker.patch(
            cash_request_detail_url(cash_request.id),
            {"otp": otp or cash_request.otp},
            format="json",
        )

    def test_owner_sends_cash_and_worker_hands_it_over_success(self, mock_sms):
        # Given the owner sends a request and the worker finds it by driver code
        created = self.request_cash()
        cash_request = CompanyCashRequest.objects.get()
        found = self.worker.get(
            f"{cash_request_list_url()}?driver_code={self.driver.code}"
        )

        # When the worker hands over the cash with the OTP
        handed_over = self.hand_over(cash_request)

        # Then both sides are charged their fee and everyone is notified
        assert created.status_code == status.HTTP_201_CREATED, created.data
        message, phone_number = mock_sms.call_args.args
        assert cash_request.otp in message
        assert phone_number == self.driver.phone_number
        assert ids(found) == [cash_request.id]
        assert handed_over.status_code == status.HTTP_200_OK, handed_over.data
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.APPROVED
        assert cash_request.station_branch_id == self.station_branch.id
        assert cash_request.approved_by_id == self.users["worker"].id
        # 100 + 5% company fee, 100 + 2% station fee
        assert cash_request.company_cost == Decimal("105.00")
        assert cash_request.station_cost == Decimal("102.00")
        assert fresh_balance(self.company) == Decimal("895.00")
        assert fresh_balance(self.company_branch) == Decimal("1000.00")
        assert fresh_balance(self.station_branch) == Decimal("398.00")
        company_txn = CompanyKhaznaTransaction.objects.get()
        assert company_txn.amount == Decimal("105.00")
        assert company_txn.for_what == CompanyKhaznaTransaction.ForWhat.DRIVER
        assert StationKhaznaTransaction.objects.get().amount == Decimal("102.00")
        assert self.users["company_owner"].id in notification_user_ids(
            Notification.NotificationType.GENERAL, title_contains=cash_request.otp
        )
        assert notification_user_ids(Notification.NotificationType.MONEY) == {
            self.users[key].id
            for key in (
                "company_owner",
                "company_manager",
                "station_owner",
                "station_manager",
                "worker",
            )
        }

    def test_handed_over_cash_shows_up_for_everyone_success(self):
        # Given a handed-over cash request
        self.request_cash()
        cash_request = CompanyCashRequest.objects.get()
        self.hand_over(cash_request)
        today = timezone.localdate().isoformat()

        # When each role reads its own view of it
        worker_list = self.worker.get(cash_request_list_url())
        owner_view = self.owner.get(cash_request_detail_url(cash_request.id))
        report = sign_in("station", self.users["station_owner"]).get(
            reports_url(date_from=today, date_to=today)
        )

        # Then each sees the request with the amount relevant to their side
        assert ids(worker_list) == [cash_request.id]
        # company roles see what they paid, station roles what they get back
        assert owner_view.data["amount"] == "105.00"
        assert worker_list.data["results"][0]["amount"] == "102.00"
        assert report.data["cash_request_balance"] == Decimal("100.00")

    def test_branch_manager_request_is_paid_by_the_branch_success(self):
        # Given a branch manager creates the request
        created = self.request_cash(self.manager)
        cash_request = CompanyCashRequest.objects.get()

        # When the worker hands it over
        handed_over = self.hand_over(cash_request)

        # Then the branch pays, not the company
        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert handed_over.status_code == status.HTTP_200_OK, handed_over.data
        assert fresh_balance(self.company_branch) == Decimal("895.00")
        assert fresh_balance(self.company) == Decimal("1000.00")

    @pytest.mark.parametrize(
        ("actor", "payer"), [("owner", "company"), ("manager", "company_branch")]
    )
    def test_cancel_refunds_whoever_paid_success(self, actor, payer):
        # Given an in-progress request that charged its payer
        client = getattr(self, actor)
        self.request_cash(client)
        cash_request = CompanyCashRequest.objects.get()
        charged = fresh_balance(getattr(self, payer))

        # When the creator cancels it
        response = client.delete(cash_request_detail_url(cash_request.id))

        # Then it is rejected and the payer is refunded
        assert response.status_code == status.HTTP_204_NO_CONTENT
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.REJECTED
        assert charged == Decimal("895.00")
        assert fresh_balance(getattr(self, payer)) == Decimal("1000.00")

    def test_second_request_for_the_same_driver_fail(self):
        # Given a driver who already has an in-progress request
        self.request_cash()

        # When a second request is made for the same driver
        response = self.request_cash()

        # Then it is rejected and only the first charge stands
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CompanyCashRequest.objects.count() == 1
        assert fresh_balance(self.company) == Decimal("895.00")

    def test_hand_over_with_a_wrong_otp_fail(self):
        # Given an in-progress request
        self.request_cash()
        cash_request = CompanyCashRequest.objects.get()
        wrong_otp = "0" if cash_request.otp != "0" else "1"

        # When the worker hands it over with the wrong OTP
        response = self.hand_over(cash_request, otp=wrong_otp)

        # Then it is rejected and the station is not charged
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.IN_PROGRESS
        assert fresh_balance(self.station_branch) == Decimal("500.00")
        assert not StationKhaznaTransaction.objects.exists()

    def test_hand_over_twice_fail(self):
        # Given an already handed-over request
        self.request_cash()
        cash_request = CompanyCashRequest.objects.get()
        self.hand_over(cash_request)

        # When the worker hands it over a second time
        response = self.hand_over(cash_request)

        # Then it is rejected and the station is charged only once
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert fresh_balance(self.station_branch) == Decimal("398.00")
        assert StationKhaznaTransaction.objects.count() == 1

    def test_cancel_after_hand_over_fail(self):
        # Given an already handed-over request
        self.request_cash()
        cash_request = CompanyCashRequest.objects.get()
        self.hand_over(cash_request)

        # When the owner tries to cancel it
        response = self.owner.delete(cash_request_detail_url(cash_request.id))

        # Then it is rejected and stays approved
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.APPROVED
        assert fresh_balance(self.company) == Decimal("895.00")

    def test_manager_cannot_cancel_the_owners_request_fail(self):
        # Given a request created by the owner
        self.request_cash()
        cash_request = CompanyCashRequest.objects.get()

        # When a branch manager tries to cancel it
        response = self.manager.delete(cash_request_detail_url(cash_request.id))

        # Then it is forbidden and the request stays in progress
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["code"] == "permission_denied"
        cash_request.refresh_from_db()
        assert cash_request.status == CompanyCashRequest.Status.IN_PROGRESS

    def test_request_more_than_the_balance_fail(self):
        # Given a company funded with 1000 (from setup)
        # When the owner requests more than that
        response = self.request_cash(amount="2000.00")

        # Then it is rejected and nothing is charged
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not CompanyCashRequest.objects.exists()
        assert fresh_balance(self.company) == Decimal("1000.00")

    def test_request_for_the_whole_balance_overdraws_by_the_fee_fail(self):
        """Open issue: the balance check compares the amount without the fee,
        so asking for the whole balance leaves the company at -fee."""
        # Given a company funded with exactly 1000 (from setup)
        # When the owner requests the whole balance
        response = self.request_cash(amount="1000.00")

        # Then it is accepted and the company is overdrawn by the fee
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert fresh_balance(self.company) == Decimal("-50.00")
