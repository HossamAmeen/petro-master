from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)
from apps.companies.admin import CarOperationAdmin
from apps.companies.models.company_models import Car
from apps.companies.models.operation_model import CarOperation
from apps.companies.operation_clone import CloneError, clone_car_operation
from apps.companies.tests.helpers import set_balance
from apps.notifications.models import Notification
from apps.stations.tests.helpers import (
    gas_url,
    image_file,
    prepare_gas_for_amount,
    worker_client,
)

pytestmark = pytest.mark.django_db

NON_CAR_SOURCES = [Car.BalanceSource.BRANCH, Car.BalanceSource.COMPANY]


@pytest.fixture
def source_operation(
    car_operation_factory, company_car, company_branch, branch, service
):
    company_branch.fees = Decimal("10.00")
    company_branch.save(update_fields=["fees"])
    branch.fees = Decimal("2.00")
    branch.balance = Decimal("10000.00")
    branch.save(update_fields=["fees", "balance"])
    company_car.balance = Decimal("5000.00")
    company_car.permitted_fuel_amount = 80
    company_car.tank_capacity = 100
    company_car.save(
        update_fields=["balance", "permitted_fuel_amount", "tank_capacity"]
    )
    return car_operation_factory()


def clone_url(operation):
    return reverse("admin:companies_caroperation_clone", args=[operation.pk])


class CloneTestCase:
    """Shared arrangement for the tests that clone `source_operation` directly."""

    @pytest.fixture(autouse=True)
    def setup(self, source_operation, admin_user):
        self.source = source_operation
        self.user = admin_user

    def clone(self, amount="20.00"):
        return clone_car_operation(
            source=self.source, amount=Decimal(amount), user=self.user
        )

    def complete_source(self):
        self.source.status = CarOperation.OperationStatus.COMPLETED
        self.source.save(update_fields=["status"])


class TestCloneCarOperation(CloneTestCase):
    def test_copies_every_field_except_audit_columns(self):
        clone = self.clone()

        assert clone.pk != self.source.pk
        assert clone.code and clone.code != self.source.code
        assert clone.created_by == self.user
        assert clone.updated_by == self.user
        assert clone.created > self.source.created

        for field in (
            "status",
            "start_time",
            "end_time",
            "duration",
            "unit",
            "fuel_type",
            "car_meter",
            "car_first_meter",
            "car_id",
            "driver_id",
            "station_branch_id",
            "worker_id",
            "service_id",
        ):
            assert getattr(clone, field) == getattr(self.source, field), field

    def test_recalculates_money_from_the_new_amount(self):
        # service cost 10, company branch fees 10%, station branch fees 2
        clone = self.clone()

        assert clone.amount == Decimal("20.00")
        assert clone.cost == Decimal("200.00")
        assert clone.company_cost == Decimal("220.00")
        assert clone.station_cost == Decimal("240.00")
        assert clone.profits == Decimal("-20.00")

    def test_rejects_amount_above_the_available_liters(self):
        with pytest.raises(CloneError, match="الحد الأقصى"):
            self.clone("500.00")

        assert CarOperation.objects.count() == 1

    def test_rejects_a_non_positive_amount(self):
        with pytest.raises(CloneError):
            self.clone("0.00")

    def test_rejects_an_operation_without_a_service(self):
        self.source.service = None
        self.source.save(update_fields=["service"])

        with pytest.raises(CloneError):
            self.clone()

    def test_pending_clone_leaves_balances_untouched(self, company_car, branch):
        self.clone()

        company_car.refresh_from_db()
        branch.refresh_from_db()
        assert company_car.balance == Decimal("5000.00")
        assert branch.balance == Decimal("10000.00")
        assert not CompanyKhaznaTransaction.objects.exists()
        assert not StationKhaznaTransaction.objects.exists()

    def test_completed_clone_applies_the_financial_effects(
        self, company_car, branch, mock_firebase_notifications
    ):
        self.complete_source()

        clone = self.clone()

        company_car.refresh_from_db()
        branch.refresh_from_db()
        assert company_car.balance == Decimal("5000.00") - clone.company_cost
        assert branch.balance == Decimal("10000.00") - clone.station_cost

        company_transaction = CompanyKhaznaTransaction.objects.get()
        station_transaction = StationKhaznaTransaction.objects.get()
        assert company_transaction.amount == clone.company_cost
        assert station_transaction.amount == clone.station_cost
        assert company_transaction.is_internal is False
        assert station_transaction.is_internal is False

    def test_completed_clone_creates_one_transaction_per_side(
        self, company, branch, mock_firebase_notifications
    ):
        self.complete_source()

        clone = self.clone()

        # both models share the KhaznaTransaction table, so two rows in total
        # means nothing was written twice on either side
        assert KhaznaTransaction.objects.count() == 2
        assert list(
            CompanyKhaznaTransaction.objects.values_list(
                "company_id", "amount", "is_internal"
            )
        ) == [(company.id, clone.company_cost, False)]
        assert list(
            StationKhaznaTransaction.objects.values_list(
                "station_id", "amount", "is_internal"
            )
        ) == [(branch.station_id, clone.station_cost, False)]
        assert not CompanyKhaznaTransaction.objects.filter(
            amount=clone.station_cost
        ).exists()
        assert not StationKhaznaTransaction.objects.filter(
            amount=clone.company_cost
        ).exists()

    def test_transaction_description_carries_the_arabic_clone_note(
        self, mock_firebase_notifications
    ):
        self.complete_source()

        self.clone()

        expected = f"نسخة من العملية رقم {self.source.code}"
        assert expected in CompanyKhaznaTransaction.objects.get().description
        assert expected in StationKhaznaTransaction.objects.get().description

    def test_completed_clone_notifies_the_worker(
        self,
        station_worker,
        mock_firebase_notifications,
        django_capture_on_commit_callbacks,
    ):
        self.complete_source()

        with django_capture_on_commit_callbacks(execute=True):
            self.clone()

        assert Notification.objects.filter(user=station_worker).exists()
        # bulk_create would skip the post_save hook that pushes FCM
        assert mock_firebase_notifications.called

    def test_notifications_wait_for_the_commit(
        self, mock_firebase_notifications, django_capture_on_commit_callbacks
    ):
        self.complete_source()

        with django_capture_on_commit_callbacks() as callbacks:
            self.clone()

        assert not Notification.objects.exists()
        assert not mock_firebase_notifications.called
        assert len(callbacks) == 2  # station fan-out, company fan-out

    def test_failure_midway_rolls_back_the_whole_clone(
        self,
        company_car,
        branch,
        mock_firebase_notifications,
        django_capture_on_commit_callbacks,
    ):
        """The company transaction is the last write, after every other one."""
        self.complete_source()

        with (
            django_capture_on_commit_callbacks(execute=True) as callbacks,
            patch(
                "apps.companies.operation_clone.generate_company_transaction",
                side_effect=RuntimeError("db down"),
            ),
            pytest.raises(RuntimeError),
        ):
            self.clone()

        company_car.refresh_from_db()
        branch.refresh_from_db()
        assert CarOperation.objects.count() == 1
        assert company_car.balance == Decimal("5000.00")
        assert branch.balance == Decimal("10000.00")
        assert not KhaznaTransaction.objects.exists()
        assert not Notification.objects.exists()
        assert callbacks == []
        assert not mock_firebase_notifications.called


def test_changelist_exposes_a_clone_button(source_operation):
    admin_instance = admin.site._registry[CarOperation]

    assert "clone_button" in admin_instance.list_display
    assert clone_url(source_operation) in admin_instance.clone_button(source_operation)


@pytest.fixture
def admin_session(settings):
    """The project keeps sessions in redis, which the test run has no access to."""
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.db"
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }


class TestCloneAdminView:
    @pytest.fixture(autouse=True)
    def setup(self, admin_session, admin_client, source_operation):
        """`admin_session` comes first: `admin_client` logs in on setup."""
        self.client = admin_client
        self.source = source_operation
        self.url = clone_url(source_operation)

    def test_get_prefills_the_source_amount(self):
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert response.context["form"].initial["amount"] == self.source.amount

    def test_post_rolls_back_the_clone_when_the_history_entry_fails(self):
        self.source.status = CarOperation.OperationStatus.COMPLETED
        self.source.save(update_fields=["status"])

        with (
            patch.object(
                CarOperationAdmin, "log_addition", side_effect=RuntimeError("boom")
            ),
            pytest.raises(RuntimeError),
        ):
            self.client.post(self.url, {"amount": "20.00"})

        assert CarOperation.objects.count() == 1
        assert not KhaznaTransaction.objects.exists()

    def test_post_creates_the_clone_and_redirects_to_it(self):
        response = self.client.post(self.url, {"amount": "20.00"})

        clone = CarOperation.objects.exclude(pk=self.source.pk).get()
        assert response.status_code == 302
        assert response.url == reverse(
            "admin:companies_caroperation_change", args=[clone.pk]
        )
        assert clone.amount == Decimal("20.00")
        assert clone.cost == Decimal("200.00")

    def test_post_of_a_completed_operation_creates_one_transaction_per_side(
        self, mock_firebase_notifications
    ):
        self.source.status = CarOperation.OperationStatus.COMPLETED
        self.source.save(update_fields=["status"])

        self.client.post(self.url, {"amount": "20.00"})

        clone = CarOperation.objects.exclude(pk=self.source.pk).get()
        assert KhaznaTransaction.objects.count() == 2
        assert list(
            CompanyKhaznaTransaction.objects.values_list("amount", "is_internal")
        ) == [(clone.company_cost, False)]
        assert list(
            StationKhaznaTransaction.objects.values_list("amount", "is_internal")
        ) == [(clone.station_cost, False)]

    def test_post_with_an_impossible_amount_redisplays_the_form(self):
        response = self.client.post(self.url, {"amount": "500.00"})

        assert response.status_code == 200
        assert response.context["form"].errors["amount"]
        assert CarOperation.objects.count() == 1

    def test_monthly_inventory_proxy_cannot_clone(self):
        response = self.client.get(
            reverse("admin:companies_monthlyinventory_clone", args=[self.source.pk])
        )

        assert response.status_code == 403


class TestCloneCarOperationBalanceSource(CloneTestCase):
    def fund(self, company_car, company_branch, company, balance_source, amount):
        """Point the car at a holder and fund only that holder."""
        company_car.balance_source = balance_source
        company_car.save(update_fields=["balance_source"])
        holder = (
            company_branch if balance_source == Car.BalanceSource.BRANCH else company
        )
        set_balance(holder, amount)
        return holder

    @pytest.mark.parametrize("balance_source", NON_CAR_SOURCES)
    def test_completed_clone_deducts_from_the_configured_holder(
        self,
        balance_source,
        company_car,
        company_branch,
        company,
        mock_firebase_notifications,
    ):
        holder = self.fund(
            company_car, company_branch, company, balance_source, "1000.00"
        )
        self.complete_source()

        clone = self.clone()

        company_car.refresh_from_db()
        holder.refresh_from_db()
        assert clone.company_cost == Decimal("220.00")
        assert holder.balance == Decimal("1000.00") - clone.company_cost
        assert company_car.balance == Decimal("5000.00")

    @pytest.mark.parametrize("balance_source", NON_CAR_SOURCES)
    def test_available_liters_come_from_the_holder_balance(
        self, balance_source, company_car, company_branch, company
    ):
        self.fund(company_car, company_branch, company, balance_source, "100.00")
        # company liter cost = 11, floor(100/11) = 9 even though the car holds 5000

        with pytest.raises(CloneError) as excinfo:
            self.clone()

        assert "9" in str(excinfo.value)
        assert CarOperation.objects.count() == 1

    @pytest.mark.parametrize("balance_source", NON_CAR_SOURCES)
    def test_pending_clone_leaves_the_holder_untouched(
        self, balance_source, company_car, company_branch, company
    ):
        holder = self.fund(
            company_car, company_branch, company, balance_source, "1000.00"
        )

        self.clone()

        holder.refresh_from_db()
        assert holder.balance == Decimal("1000.00")

    def test_car_sourced_clone_still_deducts_the_car(
        self, company_car, company_branch, company, mock_firebase_notifications
    ):
        set_balance(company_branch, "1000.00")
        set_balance(company, "1000.00")
        self.complete_source()

        clone = self.clone()

        company_car.refresh_from_db()
        company_branch.refresh_from_db()
        company.refresh_from_db()
        assert company_car.balance == Decimal("5000.00") - clone.company_cost
        assert company_branch.balance == Decimal("1000.00")
        assert company.balance == Decimal("1000.00")


MONEY_FIELDS = ("cost", "company_cost", "station_cost", "profits")
ALL_SOURCES = [Car.BalanceSource.CAR, *NON_CAR_SOURCES]


def current_balance(instance):
    return type(instance).objects.values_list("balance", flat=True).get(pk=instance.pk)


class TestCloneMatchesTheCompleteGasApi:
    """
    Completes an operation through StationGasOperationAPIView, then clones it
    with the same amount: the clone must charge exactly what the API charged.
    """

    AMOUNT = "17.33"

    @pytest.fixture(autouse=True)
    def setup(
        self,
        auth_client,
        admin_user,
        station_worker,
        station,
        branch,
        company_branch,
        car,
        service,
        gas_operation,
    ):
        # uneven prices and a fractional amount so every formula has to round
        service.cost = Decimal("13.75")
        service.save(update_fields=["cost"])
        company_branch.fees = Decimal("7.50")  # percent of the litre price
        company_branch.save(update_fields=["fees"])
        branch.fees = Decimal("0.35")  # EGP added per litre
        branch.save(update_fields=["fees"])
        set_balance(branch, "5000.00")

        self.client = worker_client(auth_client, station_worker, station)
        self.user = admin_user
        self.branch = branch
        self.car = car
        self.operation = gas_operation

    def fund(self, balance_source):
        self.car.balance_source = balance_source
        self.car.save(update_fields=["balance_source"])
        holder = self.car.balance_holder
        set_balance(holder, "1000.00")
        return holder

    def charge(self, action, holder):
        """Run `action` and report the money it moved."""
        holder_before = current_balance(holder)
        branch_before = current_balance(self.branch)
        company_ids = set(CompanyKhaznaTransaction.objects.values_list("pk", flat=True))
        station_ids = set(StationKhaznaTransaction.objects.values_list("pk", flat=True))

        operation = action()

        operation.refresh_from_db()
        return {
            "costs": {field: getattr(operation, field) for field in MONEY_FIELDS},
            "holder_deducted": holder_before - current_balance(holder),
            "station_branch_deducted": branch_before - current_balance(self.branch),
            "company_transactions": list(
                CompanyKhaznaTransaction.objects.exclude(
                    pk__in=company_ids
                ).values_list("amount", flat=True)
            ),
            "station_transactions": list(
                StationKhaznaTransaction.objects.exclude(
                    pk__in=station_ids
                ).values_list("amount", flat=True)
            ),
        }

    def complete_through_api(self):
        prepare_gas_for_amount(self.operation)
        response = self.client.patch(
            gas_url(self.operation.id),
            {"amount": self.AMOUNT, "fuel_image": image_file("fuel.png")},
            format="multipart",
        )
        assert response.status_code == 200, response.data
        return self.operation

    def mark_source_completed(self):
        self.operation.status = CarOperation.OperationStatus.COMPLETED
        self.operation.save(update_fields=["status"])

    def clone_completed_operation(self):
        return clone_car_operation(
            source=self.operation, amount=Decimal(self.AMOUNT), user=self.user
        )

    @pytest.mark.parametrize("balance_source", ALL_SOURCES)
    def test_clone_charges_what_the_api_charged_success(self, balance_source):
        holder = self.fund(balance_source)
        api = self.charge(self.complete_through_api, holder)

        clone = self.charge(self.clone_completed_operation, holder)

        assert clone == api

    def test_money_follows_the_complete_api_formulas_success(self):
        holder = self.fund(Car.BalanceSource.CAR)
        self.mark_source_completed()

        clone = self.charge(self.clone_completed_operation, holder)

        # company litre = 13.75 + 7.5% = 14.78125 ; station litre = 13.75 + 0.35
        assert clone["costs"] == {
            "cost": Decimal("238.29"),
            "company_cost": Decimal("256.16"),
            "station_cost": Decimal("244.35"),
            "profits": Decimal("11.81"),
        }
        assert clone["holder_deducted"] == Decimal("256.16")
        assert clone["station_branch_deducted"] == Decimal("244.35")

    def test_station_is_charged_station_cost_not_company_cost_success(self):
        holder = self.fund(Car.BalanceSource.CAR)
        self.mark_source_completed()

        clone = self.charge(self.clone_completed_operation, holder)

        station_cost = clone["costs"]["station_cost"]
        company_cost = clone["costs"]["company_cost"]
        assert station_cost != company_cost
        assert clone["station_transactions"] == [station_cost]
        assert clone["company_transactions"] == [company_cost]
