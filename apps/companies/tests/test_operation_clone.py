from decimal import Decimal

import pytest
from django.contrib import admin
from django.urls import reverse

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.companies.models.operation_model import CarOperation
from apps.companies.operation_clone import CloneError, clone_car_operation
from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def source_operation(car_operation_factory, company_car, company_branch, branch, service):
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


class TestCloneCarOperation:
    def test_copies_every_field_except_audit_columns(
        self, source_operation, admin_user
    ):
        clone = clone_car_operation(
            source=source_operation, amount=Decimal("20.00"), user=admin_user
        )

        assert clone.pk != source_operation.pk
        assert clone.code and clone.code != source_operation.code
        assert clone.created_by == admin_user
        assert clone.updated_by == admin_user
        assert clone.created > source_operation.created

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
            assert getattr(clone, field) == getattr(source_operation, field), field

    def test_recalculates_money_from_the_new_amount(
        self, source_operation, admin_user
    ):
        # service cost 10, company branch fees 10%, station branch fees 2
        clone = clone_car_operation(
            source=source_operation, amount=Decimal("20.00"), user=admin_user
        )

        assert clone.amount == Decimal("20.00")
        assert clone.cost == Decimal("200.00")
        assert clone.company_cost == Decimal("220.00")
        assert clone.station_cost == Decimal("240.00")
        assert clone.profits == Decimal("-20.00")

    def test_rejects_amount_above_the_available_liters(
        self, source_operation, admin_user
    ):
        with pytest.raises(CloneError, match="الحد الأقصى"):
            clone_car_operation(
                source=source_operation, amount=Decimal("500.00"), user=admin_user
            )
        assert CarOperation.objects.count() == 1

    def test_rejects_a_non_positive_amount(self, source_operation, admin_user):
        with pytest.raises(CloneError):
            clone_car_operation(
                source=source_operation, amount=Decimal("0.00"), user=admin_user
            )

    def test_rejects_an_operation_without_a_service(
        self, source_operation, admin_user
    ):
        source_operation.service = None
        source_operation.save(update_fields=["service"])

        with pytest.raises(CloneError):
            clone_car_operation(
                source=source_operation, amount=Decimal("20.00"), user=admin_user
            )

    def test_pending_clone_leaves_balances_untouched(
        self, source_operation, company_car, branch, admin_user
    ):
        clone_car_operation(
            source=source_operation, amount=Decimal("20.00"), user=admin_user
        )

        company_car.refresh_from_db()
        branch.refresh_from_db()
        assert company_car.balance == Decimal("5000.00")
        assert branch.balance == Decimal("10000.00")
        assert not CompanyKhaznaTransaction.objects.exists()
        assert not StationKhaznaTransaction.objects.exists()

    def test_completed_clone_applies_the_financial_effects(
        self,
        source_operation,
        company_car,
        branch,
        admin_user,
        mock_firebase_notifications,
    ):
        source_operation.status = CarOperation.OperationStatus.COMPLETED
        source_operation.save(update_fields=["status"])

        clone = clone_car_operation(
            source=source_operation, amount=Decimal("20.00"), user=admin_user
        )

        company_car.refresh_from_db()
        branch.refresh_from_db()
        assert company_car.balance == Decimal("5000.00") - clone.company_cost
        assert branch.balance == Decimal("10000.00") - clone.station_cost

        company_transaction = CompanyKhaznaTransaction.objects.get()
        station_transaction = StationKhaznaTransaction.objects.get()
        assert company_transaction.amount == clone.company_cost
        assert station_transaction.amount == clone.station_cost
        assert company_transaction.is_internal is True
        assert station_transaction.is_internal is False

    def test_transaction_description_carries_the_arabic_clone_note(
        self, source_operation, admin_user, mock_firebase_notifications
    ):
        source_operation.status = CarOperation.OperationStatus.COMPLETED
        source_operation.save(update_fields=["status"])

        clone_car_operation(
            source=source_operation, amount=Decimal("20.00"), user=admin_user
        )

        expected = f"نسخة من العملية رقم {source_operation.code}"
        assert expected in CompanyKhaznaTransaction.objects.get().description
        assert expected in StationKhaznaTransaction.objects.get().description

    def test_completed_clone_notifies_the_worker(
        self, source_operation, station_worker, admin_user, mock_firebase_notifications
    ):
        source_operation.status = CarOperation.OperationStatus.COMPLETED
        source_operation.save(update_fields=["status"])

        clone_car_operation(
            source=source_operation, amount=Decimal("20.00"), user=admin_user
        )

        assert Notification.objects.filter(user=station_worker).exists()
        # bulk_create would skip the post_save hook that pushes FCM
        assert mock_firebase_notifications.called


def test_changelist_exposes_a_clone_button(source_operation):
    admin_instance = admin.site._registry[CarOperation]

    assert "clone_button" in admin_instance.list_display
    assert reverse(
        "admin:companies_caroperation_clone", args=[source_operation.pk]
    ) in admin_instance.clone_button(source_operation)


@pytest.fixture
def admin_session(settings):
    """The project keeps sessions in redis, which the test run has no access to."""
    settings.SESSION_ENGINE = "django.contrib.sessions.backends.db"
    settings.CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }


@pytest.mark.usefixtures("admin_session")
class TestCloneAdminView:
    def clone_url(self, operation):
        return reverse("admin:companies_caroperation_clone", args=[operation.pk])

    def test_get_prefills_the_source_amount(self, admin_client, source_operation):
        response = admin_client.get(self.clone_url(source_operation))

        assert response.status_code == 200
        assert response.context["form"].initial["amount"] == source_operation.amount

    def test_post_creates_the_clone_and_redirects_to_it(
        self, admin_client, source_operation
    ):
        response = admin_client.post(
            self.clone_url(source_operation), {"amount": "20.00"}
        )

        clone = CarOperation.objects.exclude(pk=source_operation.pk).get()
        assert response.status_code == 302
        assert response.url == reverse(
            "admin:companies_caroperation_change", args=[clone.pk]
        )
        assert clone.amount == Decimal("20.00")
        assert clone.cost == Decimal("200.00")

    def test_post_with_an_impossible_amount_redisplays_the_form(
        self, admin_client, source_operation
    ):
        response = admin_client.post(
            self.clone_url(source_operation), {"amount": "500.00"}
        )

        assert response.status_code == 200
        assert response.context["form"].errors["amount"]
        assert CarOperation.objects.count() == 1

    def test_monthly_inventory_proxy_cannot_clone(
        self, admin_client, source_operation
    ):
        response = admin_client.get(
            reverse("admin:companies_monthlyinventory_clone", args=[source_operation.pk])
        )

        assert response.status_code == 403
