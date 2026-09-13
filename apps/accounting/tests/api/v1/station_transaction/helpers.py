from django.urls import reverse


def station_transaction_list_url():
    return reverse("station-khazna-transactions-list")


def station_transaction_detail_url(pk):
    return reverse("station-khazna-transactions-detail", kwargs={"pk": pk})


def create_payload(station, station_branch, **overrides):
    payload = {
        "station": station.id,
        "station_branch": station_branch.id,
        "amount": "10.00",
        "is_incoming": True,
        "status": "pending",
    }
    payload.update(overrides)
    return payload
