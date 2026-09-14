from decimal import Decimal

import pytest
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import admin_list_filter
from django.urls import reverse

from apps.companies.admin import BalanceRangeFilter
from apps.companies.models.company_models import Car

pytestmark = pytest.mark.django_db


def car_changelist_url():
    return reverse("admin:companies_car_changelist")


class TestCarAdminBalanceFilter:
    """
    Built through `get_changelist_instance`, which applies every list filter
    exactly as the changelist view does, without rendering the whole page.
    """

    @pytest.fixture(autouse=True)
    def setup(self, rf, admin_user, car_factory):
        self.rf = rf
        self.user = admin_user
        self.model_admin = admin.site._registry[Car]
        self.empty_car = car_factory(balance=Decimal("0.00"))
        self.low_car = car_factory(balance=Decimal("150.00"))
        self.rich_car = car_factory(balance=Decimal("500.00"))

    def changelist(self, params):
        request = self.rf.get(car_changelist_url(), params)
        request.user = self.user
        return self.model_admin.get_changelist_instance(request)

    def filtered_cars(self, params):
        return set(self.changelist(params).queryset)

    def test_balance_filter_is_registered_success(self):
        assert BalanceRangeFilter in self.model_admin.list_filter

    def test_filter_renders_the_submitted_bounds_success(self):
        changelist = self.changelist({"balance_min": "100", "balance_max": "450.5"})
        spec = next(
            spec
            for spec in changelist.filter_specs
            if isinstance(spec, BalanceRangeFilter)
        )

        html = admin_list_filter(changelist, spec)

        assert 'name="balance_min"' in html
        assert 'value="100"' in html
        assert 'name="balance_max"' in html
        assert 'value="450.5"' in html

    def test_without_bounds_lists_every_car_success(self):
        cars = self.filtered_cars({})

        assert cars == {self.empty_car, self.low_car, self.rich_car}

    def test_minimum_is_inclusive_success(self):
        cars = self.filtered_cars({"balance_min": "150"})

        assert cars == {self.low_car, self.rich_car}

    def test_maximum_is_inclusive_success(self):
        cars = self.filtered_cars({"balance_max": "150.00"})

        assert cars == {self.empty_car, self.low_car}

    def test_minimum_and_maximum_together_success(self):
        cars = self.filtered_cars({"balance_min": "100", "balance_max": "499.99"})

        assert cars == {self.low_car}

    def test_zero_bounds_find_cars_without_balance_success(self):
        cars = self.filtered_cars({"balance_min": "0", "balance_max": "0"})

        assert cars == {self.empty_car}

    def test_combines_with_other_list_filters_success(self, car_factory):
        kia_car = car_factory(brand="Kia", balance=Decimal("900.00"))
        car_factory(brand="Kia", balance=Decimal("50.00"))

        cars = self.filtered_cars({"balance_min": "200", "brand": "Kia"})

        assert cars == {kia_car}

    def test_minimum_above_maximum_lists_nothing_fail(self):
        cars = self.filtered_cars({"balance_min": "500", "balance_max": "100"})

        assert cars == set()

    @pytest.mark.parametrize("bound", ["abc", "nan", "inf", ""])
    def test_unusable_bound_is_ignored_fail(self, bound):
        # a leaked param would raise IncorrectLookupParameters instead
        cars = self.filtered_cars({"balance_min": bound, "balance_max": bound})

        assert cars == {self.empty_car, self.low_car, self.rich_car}
