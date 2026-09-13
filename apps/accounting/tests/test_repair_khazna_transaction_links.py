from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from apps.accounting.helpers import generate_station_transaction
from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)

pytestmark = pytest.mark.django_db

COMMAND = "repair_khazna_transaction_links"
ORPHAN_COMPANY_ID = 900001
ORPHAN_STATION_ID = 900002


def run(*args):
    out = StringIO()
    call_command(COMMAND, *args, stdout=out)
    return out.getvalue()


def execute(sql, params=()):
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall() if cursor.description else None


def insert_company_child(pk, company):
    """A company row written straight to its table, as a partial restore leaves it."""
    execute(
        "INSERT INTO accounting_companykhaznatransaction "
        "(khaznatransaction_ptr_id, company_id, for_what) VALUES (%s, %s, %s)",
        [pk, company.id, CompanyKhaznaTransaction.ForWhat.BRANCH],
    )


def insert_station_child(pk, station):
    execute(
        "INSERT INTO accounting_stationkhaznatransaction "
        "(khaznatransaction_ptr_id, station_id) VALUES (%s, %s)",
        [pk, station.id],
    )


def child_ids(model):
    """Every child row, including the orphans the ORM join cannot see."""
    rows = execute(
        f"SELECT khaznatransaction_ptr_id FROM {model._meta.db_table} ORDER BY 1"
    )
    return [row[0] for row in rows]


@pytest.fixture
def leftover_rows():
    """
    Orphans break the foreign-key check Django runs when the test ends, so
    whatever a test leaves behind is removed first.
    """
    yield
    for model in (CompanyKhaznaTransaction, StationKhaznaTransaction):
        execute(
            f"DELETE FROM {model._meta.db_table} WHERE khaznatransaction_ptr_id "
            "NOT IN (SELECT id FROM accounting_khaznatransaction)"
        )


class TestRepairKhaznaTransactionLinks:
    """
    Mirrors the staging data: two real transactions, each also claimed by a
    stale child row of the other side, plus orphans waiting for future ids.
    """

    @pytest.fixture(autouse=True)
    def setup(
        self,
        leftover_rows,
        station_transaction_factory,
        company_transaction_factory,
        company,
        other_company,
        station,
        station_factory,
    ):
        self.station_transaction = station_transaction_factory(amount=Decimal("309.15"))
        self.company_transaction = company_transaction_factory(amount=Decimal("310.58"))
        self.real_company = company
        self.real_station = station
        self.stale_company = other_company
        self.stale_station = station_factory()

        insert_company_child(self.station_transaction.pk, self.stale_company)
        insert_station_child(self.company_transaction.pk, self.stale_station)
        insert_company_child(ORPHAN_COMPANY_ID, self.stale_company)
        insert_station_child(ORPHAN_STATION_ID, self.stale_station)

        self.drop_stale_owners = [
            "--drop",
            f"company:{self.station_transaction.pk}",
            "--drop",
            f"station:{self.company_transaction.pk}",
        ]

    def test_dry_run_reports_without_changing_anything_success(self):
        output = run()

        assert "2 transaction(s) attached to both a company and a station" in output
        assert f"--drop company:{self.station_transaction.pk}" in output
        assert f"--drop station:{self.company_transaction.pk}" in output
        assert self.stale_company.name in output
        assert self.stale_station.name in output
        assert "orphan company row(s) without a base transaction" in output
        assert str(ORPHAN_COMPANY_ID) in output
        assert str(ORPHAN_STATION_ID) in output
        assert "Dry run" in output
        assert child_ids(CompanyKhaznaTransaction) == [
            self.station_transaction.pk,
            self.company_transaction.pk,
            ORPHAN_COMPANY_ID,
        ]
        assert child_ids(StationKhaznaTransaction) == [
            self.station_transaction.pk,
            self.company_transaction.pk,
            ORPHAN_STATION_ID,
        ]

    def test_apply_deletes_only_the_orphans_success(self):
        output = run("--apply")

        assert child_ids(CompanyKhaznaTransaction) == [
            self.station_transaction.pk,
            self.company_transaction.pk,
        ]
        assert child_ids(StationKhaznaTransaction) == [
            self.station_transaction.pk,
            self.company_transaction.pk,
        ]
        assert KhaznaTransaction.objects.count() == 2
        assert "Still shared" in output

    def test_drop_detaches_the_stale_owners_success(self):
        output = run("--apply", *self.drop_stale_owners)

        assert list(
            CompanyKhaznaTransaction.objects.values_list("pk", "company", "amount")
        ) == [(self.company_transaction.pk, self.real_company.pk, Decimal("310.58"))]
        assert list(
            StationKhaznaTransaction.objects.values_list("pk", "station", "amount")
        ) == [(self.station_transaction.pk, self.real_station.pk, Decimal("309.15"))]
        assert KhaznaTransaction.objects.count() == 2
        assert "Still shared" not in output
        assert "No transaction is attached to both" in run()

    def test_drop_without_apply_changes_nothing_success(self):
        company_rows = child_ids(CompanyKhaznaTransaction)
        station_rows = child_ids(StationKhaznaTransaction)

        output = run(*self.drop_stale_owners)

        assert (
            f"Would detach the company owner from transaction "
            f"{self.station_transaction.pk}" in output
        )
        assert child_ids(CompanyKhaznaTransaction) == company_rows
        assert child_ids(StationKhaznaTransaction) == station_rows

    def test_drop_of_a_transaction_that_is_not_shared_fail(self):
        execute(
            "DELETE FROM accounting_stationkhaznatransaction "
            "WHERE khaznatransaction_ptr_id = %s",
            [self.company_transaction.pk],
        )

        with pytest.raises(CommandError, match="Only transactions reported as shared"):
            run("--apply", "--drop", f"company:{self.company_transaction.pk}")

        assert self.company_transaction.pk in child_ids(CompanyKhaznaTransaction)
        assert ORPHAN_COMPANY_ID in child_ids(CompanyKhaznaTransaction)

    def test_drop_of_both_owners_of_one_transaction_fail(self):
        pk = self.station_transaction.pk

        with pytest.raises(CommandError, match="not both"):
            run("--apply", "--drop", f"company:{pk}", "--drop", f"station:{pk}")

        assert pk in child_ids(CompanyKhaznaTransaction)
        assert pk in child_ids(StationKhaznaTransaction)

    @pytest.mark.parametrize(
        "value", ["company", "bank:1", "company:abc", "station:-3"]
    )
    def test_drop_with_a_malformed_value_fail(self, value):
        with pytest.raises(CommandError, match="--drop expects"):
            run("--apply", "--drop", value)

        assert ORPHAN_COMPANY_ID in child_ids(CompanyKhaznaTransaction)


class TestLeftoverChildRow:
    """A leftover company row sitting on the id the next transaction gets."""

    @pytest.fixture(autouse=True)
    def setup(
        self, leftover_rows, station_transaction_factory, other_company, station, branch
    ):
        self.station = station
        self.branch = branch
        latest = station_transaction_factory()
        self.next_id = latest.pk + 1
        insert_company_child(self.next_id, other_company)

    def create_station_transaction(self, admin_user):
        generate_station_transaction(
            station_id=self.station.id,
            station_branch_id=self.branch.id,
            amount=Decimal("309.15"),
            status=KhaznaTransaction.TransactionStatus.APPROVED,
            description="fueling",
            created_by_id=admin_user.id,
        )
        return StationKhaznaTransaction.objects.latest("pk")

    def test_next_transaction_shows_in_the_company_list_too_fail(self, admin_user):
        new_transaction = self.create_station_transaction(admin_user)

        assert new_transaction.pk == self.next_id
        assert CompanyKhaznaTransaction.objects.filter(pk=self.next_id).exists()

    def test_apply_keeps_the_next_transaction_on_its_own_side_success(self, admin_user):
        run("--apply")

        new_transaction = self.create_station_transaction(admin_user)

        assert new_transaction.pk == self.next_id
        assert not CompanyKhaznaTransaction.objects.filter(pk=self.next_id).exists()


class TestRepairOnHealthyData:
    def test_reports_nothing_and_changes_nothing_success(
        self, station_transaction_factory, company_transaction_factory
    ):
        station_transaction_factory()
        company_transaction_factory()

        output = run("--apply")

        assert "No transaction is attached to both" in output
        assert "No orphan company rows." in output
        assert "No orphan station rows." in output
        assert "Deleted 0 orphan company row(s)." in output
        assert CompanyKhaznaTransaction.objects.count() == 1
        assert StationKhaznaTransaction.objects.count() == 1
