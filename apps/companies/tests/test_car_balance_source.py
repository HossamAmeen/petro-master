from decimal import Decimal

import pytest
from django.contrib import admin

from apps.companies.models.company_models import Car
from apps.companies.tests.helpers import set_balance

pytestmark = pytest.mark.django_db


class TestCarBalanceSource:
    @pytest.fixture(autouse=True)
    def setup(self, car_factory, company_branch, company):
        self.car_factory = car_factory
        self.branch = company_branch
        self.company = company

    def car_with(self, balance_source, **overrides):
        return self.car_factory(balance_source=balance_source, **overrides)

    def fund_all(self, car, car_amount="100.00", branch="200.00", company="300.00"):
        set_balance(car, car_amount)
        set_balance(self.branch, branch)
        set_balance(self.company, company)

    def assert_balances(self, car, car_amount, branch, company):
        car.refresh_from_db()
        self.branch.refresh_from_db()
        self.company.refresh_from_db()
        assert car.balance == Decimal(car_amount)
        assert self.branch.balance == Decimal(branch)
        assert self.company.balance == Decimal(company)

    def test_default_balance_source_is_car_success(self, company_car):
        company_car.refresh_from_db()

        assert company_car.balance_source == Car.BalanceSource.CAR

    def test_balance_source_choice_values_success(self):
        assert Car.BalanceSource.CAR == "car"
        assert Car.BalanceSource.BRANCH == "branch"
        assert Car.BalanceSource.COMPANY == "company"
        assert [choice[0] for choice in Car.BalanceSource.choices] == [
            "car",
            "branch",
            "company",
        ]

    def test_balance_holder_is_the_car_success(self, company_car):
        assert company_car.balance_holder == company_car

    def test_balance_holder_is_the_branch_success(self):
        assert self.car_with(Car.BalanceSource.BRANCH).balance_holder == self.branch

    def test_balance_holder_is_the_company_success(self):
        assert self.car_with(Car.BalanceSource.COMPANY).balance_holder == self.company

    @pytest.mark.parametrize(
        ("balance_source", "expected"),
        [
            (Car.BalanceSource.CAR, Decimal("100.00")),
            (Car.BalanceSource.BRANCH, Decimal("200.00")),
            (Car.BalanceSource.COMPANY, Decimal("300.00")),
        ],
    )
    def test_available_balance_reads_the_holder_success(self, balance_source, expected):
        car = self.car_with(balance_source)
        self.fund_all(car)

        assert car.available_balance == expected

    @pytest.mark.parametrize(
        ("balance_source", "expected"),
        [
            (Car.BalanceSource.CAR, ("60.00", "200.00", "300.00")),
            (Car.BalanceSource.BRANCH, ("100.00", "160.00", "300.00")),
            (Car.BalanceSource.COMPANY, ("100.00", "200.00", "260.00")),
        ],
    )
    def test_deduct_balance_only_touches_the_holder_success(
        self, balance_source, expected
    ):
        car = self.car_with(balance_source)
        self.fund_all(car)

        car.deduct_balance(Decimal("40.00"))

        self.assert_balances(car, *expected)

    def test_deduct_balance_returns_the_remaining_holder_balance_success(self):
        car = self.car_with(Car.BalanceSource.BRANCH)
        set_balance(self.branch, "200.00")

        assert car.deduct_balance(Decimal("25.50")) == Decimal("174.50")

    @pytest.mark.parametrize("amount", [10, 10.0, "10.00", Decimal("10.00")])
    def test_deduct_balance_accepts_non_decimal_amounts_success(self, amount):
        car = self.car_with(Car.BalanceSource.BRANCH)
        set_balance(self.branch, "100.00")

        car.deduct_balance(amount)

        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("90.00")

    def test_deduct_balance_on_unsaved_float_balance_success(self):
        """A branch fetched without a refresh can still hold a float balance."""
        car = self.car_with(Car.BalanceSource.BRANCH)
        self.branch.balance = 100.5
        self.branch.save(update_fields=["balance"])
        car.branch.balance = 100.5

        car.deduct_balance(Decimal("0.50"))

        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("100.00")

    def test_deduct_balance_can_drive_the_holder_negative_success(self):
        car = self.car_with(Car.BalanceSource.COMPANY)
        set_balance(self.company, "10.00")

        car.deduct_balance(Decimal("25.00"))

        self.company.refresh_from_db()
        assert self.company.balance == Decimal("-15.00")

    def test_deduct_balance_persists_the_holder_success(self):
        car = self.car_with(Car.BalanceSource.BRANCH)
        set_balance(self.branch, "80.00")

        car.deduct_balance(Decimal("30.00"))

        assert car.branch.balance == Decimal("50.00")
        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("50.00")

    def test_deduct_balance_only_touches_the_balance_column_success(self):
        car = self.car_with(Car.BalanceSource.BRANCH)
        set_balance(self.branch, "80.00")
        car.branch.name = "Renamed In Memory"

        car.deduct_balance(Decimal("30.00"))

        self.branch.refresh_from_db()
        assert self.branch.balance == Decimal("50.00")
        assert self.branch.name == "Company Branch 1"

    def test_balance_source_can_be_changed_success(self, company_car):
        company_car.balance_source = Car.BalanceSource.COMPANY
        company_car.save(update_fields=["balance_source"])

        company_car.refresh_from_db()
        assert company_car.balance_source == Car.BalanceSource.COMPANY
        assert company_car.balance_holder == company_car.branch.company

    def test_branch_sourced_cars_of_the_same_branch_share_one_balance_success(self):
        first = self.car_with(Car.BalanceSource.BRANCH)
        second = self.car_with(Car.BalanceSource.BRANCH)
        set_balance(self.branch, "100.00")

        first.deduct_balance(Decimal("30.00"))

        assert Car.objects.get(pk=second.pk).available_balance == Decimal("70.00")

    def test_company_sourced_cars_of_other_branches_share_one_balance_success(
        self, second_company_branch
    ):
        car = self.car_with(Car.BalanceSource.COMPANY)
        other_branch_car = self.car_with(
            Car.BalanceSource.COMPANY, branch=second_company_branch
        )
        set_balance(self.company, "500.00")

        car.deduct_balance(Decimal("200.00"))

        reloaded = Car.objects.get(pk=other_branch_car.pk)
        assert reloaded.available_balance == Decimal("300.00")


def test_car_admin_exposes_balance_source():
    admin_instance = admin.site._registry[Car]

    assert "balance_source" in admin_instance.list_display
    assert "balance_source" in admin_instance.list_filter
    assert "balance_source" not in admin_instance.readonly_fields
