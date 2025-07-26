from django.utils import timezone

from apps.accounting.models import CompanyKhaznaTransaction, StationKhaznaTransaction
from apps.shared.generate_code import generate_unique_code


def generate_company_transaction(
    company_id,
    amount,
    status,
    description,
    approved_at=None,
    is_internal=False,
    for_what=None,
    created_by_id=None,
):
    reference_code = generate_unique_code(
        model=CompanyKhaznaTransaction,
        look_up="reference_code",
        min_value=10**8,
        max_value=10**9,
    )
    reference_code = (
        str("INT-" + str(reference_code)) if is_internal else str(reference_code)
    )
    approved_at = timezone.localtime() if not approved_at else approved_at
    CompanyKhaznaTransaction.objects.create(
        company_id=company_id,
        amount=amount,
        status=status,
        reference_code=reference_code,
        description=description,
        approved_at=approved_at,
        is_internal=is_internal,
        for_what=for_what,
        created_by_id=created_by_id,
    )


def generate_station_transaction(
    station_id,
    station_branch_id,
    amount,
    status,
    description,
    approved_at=None,
    is_internal=False,
    created_by_id=None,
):
    reference_code = generate_unique_code(
        model=StationKhaznaTransaction,
        look_up="reference_code",
        min_value=10**8,
        max_value=10**9,
    )
    approved_at = timezone.localtime() if not approved_at else approved_at
    StationKhaznaTransaction.objects.create(
        station_id=station_id,
        station_branch_id=station_branch_id,
        amount=amount,
        status=status,
        reference_code=reference_code,
        description=description,
        approved_at=approved_at,
        is_internal=is_internal,
        created_by_id=created_by_id,
    )
