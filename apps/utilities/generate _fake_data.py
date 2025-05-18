# flake8: noqa


def generate_company_transaction():
    import random
    import uuid

    company_ids = list(Company.objects.values_list("id", flat=True))
    for _ in range(100):
        for_what = random.choice(CompanyKhaznaTransaction.ForWhat.values + [None])
        CompanyKhaznaTransaction.objects.create(
            amount=random.randint(100, 5000),
            is_incoming=True,
            status=CompanyKhaznaTransaction.TransactionStatus.APPROVED,
            reference_code=str(uuid.uuid4())[:10].upper(),
            description="Test transaction",
            method=CompanyKhaznaTransaction.TransactionMethod.BANK,
            company_id=random.choice(company_ids),
            for_what=for_what,
            created_by_id=1,
            updated_by_id=1,
        )
