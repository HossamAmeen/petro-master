from django.urls import reverse


def transaction_list_url():
    return reverse("transaction-list")


def transaction_detail_url(pk):
    return reverse("transaction-detail", kwargs={"pk": pk})
