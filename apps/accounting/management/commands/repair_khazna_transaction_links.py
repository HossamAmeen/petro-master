"""
Company and station khazna transactions share the KhaznaTransaction table
(multi-table inheritance): amount, reference code and description live on the
base row, the owner (company or station) on the child row, joined by id.

A child row that outlived its base row, typically left by a partial database
restore, is picked up by whichever new transaction later receives that id. The
new transaction then shows in both admin lists, once with a foreign company or
station attached.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.accounting.models import (
    CompanyKhaznaTransaction,
    KhaznaTransaction,
    StationKhaznaTransaction,
)

SIDES = {"company": CompanyKhaznaTransaction, "station": StationKhaznaTransaction}

LISTED_IDS_LIMIT = 20


def table(model):
    return connection.ops.quote_name(model._meta.db_table)


def link_column(model):
    return connection.ops.quote_name(model._meta.pk.column)


def fetch_ids(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        return [row[0] for row in cursor.fetchall()]


def orphan_ids(model):
    """Child rows whose base row no longer exists."""
    return fetch_ids(
        f"SELECT {link_column(model)} FROM {table(model)} "
        f"WHERE {link_column(model)} NOT IN "
        f"(SELECT {link_column(KhaznaTransaction)} FROM {table(KhaznaTransaction)}) "
        "ORDER BY 1"
    )


def shared_ids():
    """Base rows claimed by a company child and a station child at once."""
    company, station = CompanyKhaznaTransaction, StationKhaznaTransaction
    return fetch_ids(
        f"SELECT company.{link_column(company)} FROM {table(company)} company "
        f"INNER JOIN {table(station)} station "
        f"ON station.{link_column(station)} = company.{link_column(company)} "
        "ORDER BY 1"
    )


def delete_orphans(model):
    with connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {table(model)} WHERE {link_column(model)} NOT IN "
            f"(SELECT {link_column(KhaznaTransaction)} FROM {table(KhaznaTransaction)})"
        )
        return cursor.rowcount


def delete_child_row(model, pk):
    """Remove only the child row; the base row and the other owner stay."""
    with connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {table(model)} WHERE {link_column(model)} = %s", [pk]
        )


def parse_drop(value):
    side, _, raw_id = value.partition(":")
    if side not in SIDES or not raw_id.isdigit():
        raise CommandError(
            f"--drop expects company:<id> or station:<id>, got {value!r}."
        )
    return side, int(raw_id)


def listed(ids):
    shown = ", ".join(str(pk) for pk in ids[:LISTED_IDS_LIMIT])
    hidden = len(ids) - LISTED_IDS_LIMIT
    return f"{shown} (+{hidden} more)" if hidden > 0 else shown


class Command(BaseCommand):
    help = (
        "Report and repair khazna transactions attached to both a company and a "
        "station, and child rows left without a base transaction. Reports only "
        "unless --apply is given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write the repair. Without it nothing is changed.",
        )
        parser.add_argument(
            "--drop",
            action="append",
            default=[],
            metavar="SIDE:ID",
            help=(
                "Detach the wrong owner of a transaction reported as shared, "
                "e.g. --drop station:45984. Repeatable."
            ),
        )

    def handle(self, *args, **options):
        drops = [parse_drop(value) for value in options["drop"]]

        with transaction.atomic():
            shared = shared_ids()
            orphans = {side: orphan_ids(model) for side, model in SIDES.items()}
            self.validate_drops(drops, shared)

            self.report_shared(shared)
            self.report_orphans(orphans)

            if not options["apply"]:
                self.report_planned_drops(drops)
                self.stdout.write(
                    self.style.WARNING(
                        "Dry run: nothing was changed. Re-run with --apply to repair."
                    )
                )
                return

            for side, model in SIDES.items():
                removed = delete_orphans(model)
                self.stdout.write(f"Deleted {removed} orphan {side} row(s).")

            for side, pk in drops:
                delete_child_row(SIDES[side], pk)
                self.stdout.write(f"Detached the {side} owner from transaction {pk}.")

        unresolved = sorted(set(shared) - {pk for _, pk in drops})
        if unresolved:
            self.stdout.write(
                self.style.WARNING(
                    f"Still shared, pick the wrong owner with --drop: {listed(unresolved)}"
                )
            )
        self.stdout.write(self.style.SUCCESS("Repair applied."))

    @staticmethod
    def validate_drops(drops, shared):
        not_shared = [f"{side}:{pk}" for side, pk in drops if pk not in shared]
        if not_shared:
            raise CommandError(
                "Only transactions reported as shared can be dropped: "
                + ", ".join(not_shared)
            )

        dropped_ids = [pk for _, pk in drops]
        both_sides = sorted({pk for pk in dropped_ids if dropped_ids.count(pk) > 1})
        if both_sides:
            raise CommandError(
                "Drop one owner per transaction, not both: "
                + ", ".join(str(pk) for pk in both_sides)
            )

    def report_shared(self, shared):
        if not shared:
            self.stdout.write(
                "No transaction is attached to both a company and a station."
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"{len(shared)} transaction(s) attached to both a company and a station. "
                "Only one owner is real: drop the one that does not match the "
                "description."
            )
        )
        companies = CompanyKhaznaTransaction.objects.filter(
            pk__in=shared
        ).select_related("company", "company_branch")
        stations = {
            row.pk: row
            for row in StationKhaznaTransaction.objects.filter(
                pk__in=shared
            ).select_related("station", "station_branch")
        }
        for company_row in companies.order_by("pk"):
            station_row = stations[company_row.pk]
            self.stdout.write(
                f"  #{company_row.pk} amount={company_row.amount} "
                f"ref={company_row.reference_code} created={company_row.created:%Y-%m-%d %H:%M}\n"
                f"    description: {company_row.description}\n"
                f"    company: {company_row.company} / {company_row.company_branch or '-'}"
                f"  ->  --drop company:{company_row.pk}\n"
                f"    station: {station_row.station} / {station_row.station_branch or '-'}"
                f"  ->  --drop station:{station_row.pk}"
            )

    def report_orphans(self, orphans):
        for side, ids in orphans.items():
            if ids:
                self.stdout.write(
                    self.style.WARNING(
                        f"{len(ids)} orphan {side} row(s) without a base transaction "
                        f"(deleted by --apply): {listed(ids)}"
                    )
                )
            else:
                self.stdout.write(f"No orphan {side} rows.")

    def report_planned_drops(self, drops):
        for side, pk in drops:
            self.stdout.write(f"Would detach the {side} owner from transaction {pk}.")
