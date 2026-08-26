from urllib.parse import urlencode

from django.urls import reverse


def with_query(url, **params):
    params = {key: value for key, value in params.items() if value is not None}
    if not params:
        return url
    return f"{url}?{urlencode(params, doseq=True)}"


def notifications_list_url(**params):
    return with_query(reverse("notification-list"), **params)


def notifications_detail_url(notification_id, **params):
    return with_query(
        reverse("notification-detail", kwargs={"pk": notification_id}),
        **params,
    )


def returned_ids(response):
    return {item["id"] for item in response.data["results"]}
