from django.utils import timezone

from apps.accounting.models import CompanyKhaznaTransaction
from apps.shared.generate_code import generate_unique_code


def generate_company_transaction(
    company_id,
    amount,
    status,
    description,
    approved_at=None,
    is_internal=False,
    for_what=None,
):
    reference_code = generate_unique_code(
        model=CompanyKhaznaTransaction, min_value=10**8, max_value=10**9
    )
    reference_code = (
        str("INT-" + str(reference_code)) if is_internal else str(reference_code)
    )
    if not approved_at:
        approved_at = timezone.now()
    CompanyKhaznaTransaction.objects.create(
        company_id=company_id,
        amount=amount,
        status=status,
        reference_code=reference_code,
        description=description,
        approved_at=approved_at,
        is_internal=is_internal,
        for_what=for_what,
    )
