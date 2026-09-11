"""Money loaded by the dashboard moves company ↔ branch ↔ car and back."""

from decimal import Decimal

import pytest
from rest_framework import status

from apps.accounting.models import CompanyKhaznaTransaction
from apps.accounting.tests.api.v1.company_transaction.helpers import (
    company_transaction_detail_url,
    company_transaction_list_url,
    create_payload,
)
from apps.companies.models.company_models import Car
from apps.companies.tests.api.v1.car.helpers import update_balance_url
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification
from apps.stations.tests.helpers import notification_user_ids

from .helpers import (
    company_branch_balance_url,
    company_home_url,
    fresh_balance,
    sign_in,
    verify,
)

pytestmark = [pytest.mark.django_db, pytest.mark.feature]

ZERO = Decimal("0.00")


def move(amount, direction):
    return {"amount": amount, "type": direction}


class TestCompanyMoney:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        admin_user,
        company,
        company_owner,
        company_branch,
        second_company_branch,
        company_branch_manager,
        fuelable_car,
    ):
        self.company = company
        self.branch = company_branch
        self.second_branch = second_company_branch
        self.manager_user = company_branch_manager
        self.car = fuelable_car
        self.admin = sign_in("dashboard", admin_user)
        self.owner = sign_in("company", company_owner)
        self.manager = sign_in("company", company_branch_manager)

    def top_up(self, client, amount, **overrides):
        payload = create_payload(
            self.company,
            self.branch,
            amount=amount,
            is_incoming=False,  # False adds to the balance
            status="approved",
        )
        payload.update(overrides)
        return client.post(company_transaction_list_url(), payload, format="json")

    def balances(self):
        return [
            fresh_balance(item)
            for item in (self.company, self.branch, self.second_branch, self.car)
        ]

    def test_dashboard_topup_moves_down_to_a_car_and_back_success(self):
        topped_up = self.top_up(self.admin, "1000.00")
        to_company = self.owner.post(
            company_branch_balance_url(self.branch.id),
            move("400.00", "subtract"),
            format="json",
        )
        to_second_branch = self.owner.post(
            company_branch_balance_url(self.second_branch.id),
            move("150.00", "add"),
            format="json",
        )
        from_company = self.owner.post(
            update_balance_url(self.car.id), move("100.00", "add"), format="json"
        )
        from_branch = self.manager.post(
            update_balance_url(self.car.id), move("50.00", "add"), format="json"
        )
        back_to_branch = self.manager.post(
            update_balance_url(self.car.id), move("30.00", "subtract"), format="json"
        )
        home = self.owner.get(company_home_url())

        assert topped_up.status_code == status.HTTP_201_CREATED, topped_up.data
        for response in (
            to_company,
            to_second_branch,
            from_company,
            from_branch,
            back_to_branch,
        ):
            assert response.status_code == status.HTTP_200_OK, response.data
        assert back_to_branch.data == {"balance": Decimal("120.00")}
        # company, branch, second branch, car
        assert self.balances() == [
            Decimal("150.00"),
            Decimal("580.00"),
            Decimal("150.00"),
            Decimal("120.00"),
        ]
        assert home.data["total_balance"] == Decimal("1000.00")
        assert CompanyKhaznaTransaction.objects.filter(is_internal=True).count() == 5
        assert self.manager_user.id in notification_user_ids(
            Notification.NotificationType.MONEY, title_contains="1000"
        )

    @pytest.mark.parametrize(
        "step",
        [
            "branch_to_company",
            "company_to_branch",
            "company_to_car",
            "branch_to_car",
            "car_to_parent",
        ],
    )
    def test_moves_without_enough_balance_fail(self, step):
        client, url, payload = {
            "branch_to_company": (
                self.owner,
                company_branch_balance_url(self.branch.id),
                move("10.00", "subtract"),
            ),
            "company_to_branch": (
                self.owner,
                company_branch_balance_url(self.branch.id),
                move("10.00", "add"),
            ),
            "company_to_car": (
                self.owner,
                update_balance_url(self.car.id),
                move("10.00", "add"),
            ),
            "branch_to_car": (
                self.manager,
                update_balance_url(self.car.id),
                move("10.00", "add"),
            ),
            "car_to_parent": (
                self.owner,
                update_balance_url(self.car.id),
                move("10.00", "subtract"),
            ),
        }[step]

        response = client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "not_enough_balance"
        assert self.balances() == [ZERO] * 4
        assert not CompanyKhaznaTransaction.objects.exists()

    @pytest.mark.parametrize(
        "balance_source", [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY]
    )
    def test_top_up_a_car_paid_by_its_branch_or_company_fail(self, balance_source):
        set_balance(self.company, "100.00")
        self.car.balance_source = balance_source
        self.car.save(update_fields=["balance_source"])

        response = self.owner.post(
            update_balance_url(self.car.id), move("10.00", "add"), format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["code"] == "balance_source_not_car"
        assert fresh_balance(self.company) == Decimal("100.00")

    def test_top_up_a_car_in_the_middle_of_a_fueling_fail(
        self, station_worker, company_driver
    ):
        set_balance(self.company, "100.00")
        set_balance(self.car, "50.00")
        verified = verify(sign_in("station", station_worker), company_driver, self.car)

        response = self.owner.post(
            update_balance_url(self.car.id), move("10.00", "add"), format="json"
        )

        assert verified.status_code == status.HTTP_200_OK, verified.data
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert fresh_balance(self.car) == Decimal("50.00")
        assert fresh_balance(self.company) == Decimal("100.00")

    def test_branch_manager_cannot_move_company_money_fail(self):
        set_balance(self.company, "100.00")

        response = self.manager.post(
            company_branch_balance_url(self.branch.id),
            move("10.00", "add"),
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert fresh_balance(self.branch) == ZERO

    def test_dashboard_approves_a_pending_topup_success(self):
        created = self.top_up(self.admin, "300.00", status="pending")
        pending_balance = fresh_balance(self.branch)

        approved = self.admin.patch(
            company_transaction_detail_url(created.data["id"]),
            {
                "company": self.company.id,
                "company_branch": self.branch.id,
                "status": "approved",
            },
            format="json",
        )
        again = self.admin.patch(
            company_transaction_detail_url(created.data["id"]),
            {
                "company": self.company.id,
                "company_branch": self.branch.id,
                "status": "approved",
            },
            format="json",
        )

        assert created.status_code == status.HTTP_201_CREATED, created.data
        assert pending_balance == ZERO
        assert approved.status_code == status.HTTP_200_OK, approved.data
        assert again.status_code == status.HTTP_400_BAD_REQUEST
        assert fresh_balance(self.branch) == Decimal("300.00")

    def test_approve_without_sending_the_branch_crashes_fail(self):
        """Known bug: the update serializer indexes `attrs["company_branch"]`,
        so the usual `{"status": "approved"}` PATCH raises a KeyError (500)."""
        created = self.top_up(self.admin, "300.00", status="pending")

        with pytest.raises(KeyError):
            self.admin.patch(
                company_transaction_detail_url(created.data["id"]),
                {"status": "approved"},
                format="json",
            )

        assert fresh_balance(self.branch) == ZERO

    def test_company_owner_can_approve_their_own_topup_success(self):
        """Open issue: company roles may create khazna transactions, including
        already-approved ones, so an owner can credit their own branch."""
        response = self.top_up(self.owner, "5000.00")

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert fresh_balance(self.branch) == Decimal("5000.00")
