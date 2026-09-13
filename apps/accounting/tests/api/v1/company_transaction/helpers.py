from django.urls import reverse


def company_transaction_list_url():
    return reverse("company-khazna-transactions-list")


def company_transaction_detail_url(pk):
    return reverse("company-khazna-transactions-detail", kwargs={"pk": pk})


def create_payload(company, company_branch, **overrides):
    payload = {
        "company": company.id,
        "company_branch": company_branch.id,
        "amount": "10.00",
        "is_incoming": True,
        "status": "pending",
    }
    payload.update(overrides)
    return payload
