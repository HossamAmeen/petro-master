from urllib.parse import urlencode

from django.urls import reverse


def with_query(url, **params):
    params = {key: value for key, value in params.items() if value is not None}
    if not params:
        return url
    return f"{url}?{urlencode(params, doseq=True)}"


def cities_list_url(**params):
    return with_query(reverse("cities-list"), **params)


def cities_detail_url(city_id, **params):
    return with_query(reverse("cities-detail", kwargs={"pk": city_id}), **params)


def districts_list_url(**params):
    return with_query(reverse("districts-list"), **params)


def districts_detail_url(district_id, **params):
    return with_query(reverse("districts-detail", kwargs={"pk": district_id}), **params)


def returned_ids(response):
    payload = response.data
    if isinstance(payload, dict) and "results" in payload:
        return {item["id"] for item in payload["results"]}
    return {item["id"] for item in payload}
