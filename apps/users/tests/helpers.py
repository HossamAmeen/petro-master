from urllib.parse import urlencode

from django.urls import reverse


def with_query(url, **params):
    params = {key: value for key, value in params.items() if value is not None}
    if not params:
        return url
    return f"{url}?{urlencode(params, doseq=True)}"


def users_list_url(**params):
    return with_query(reverse("users-list"), **params)


def users_detail_url(user_id, **params):
    return with_query(reverse("users-detail", kwargs={"pk": user_id}), **params)


def company_owners_list_url(**params):
    return with_query(reverse("company-owners-list"), **params)


def company_owners_detail_url(user_id, **params):
    return with_query(
        reverse("company-owners-detail", kwargs={"pk": user_id}), **params
    )


def company_branch_managers_list_url(**params):
    return with_query(reverse("company-branch-managers-list"), **params)


def company_branch_managers_detail_url(user_id, **params):
    return with_query(
        reverse("company-branch-managers-detail", kwargs={"pk": user_id}),
        **params,
    )


def station_owners_list_url(**params):
    return with_query(reverse("station-owners-list"), **params)


def station_owners_detail_url(user_id, **params):
    return with_query(
        reverse("station-owners-detail", kwargs={"pk": user_id}), **params
    )


def station_branch_managers_list_url(**params):
    return with_query(reverse("station-branch-managers-list"), **params)


def station_branch_managers_detail_url(user_id, **params):
    return with_query(
        reverse("station-branch-managers-detail", kwargs={"pk": user_id}),
        **params,
    )


def workers_list_url(**params):
    return with_query(reverse("workers-list"), **params)


def workers_detail_url(user_id, **params):
    return with_query(reverse("workers-detail", kwargs={"pk": user_id}), **params)


def supervisors_list_url(**params):
    return with_query(reverse("supervisors-list"), **params)


def supervisors_detail_url(user_id, **params):
    return with_query(reverse("supervisors-detail", kwargs={"pk": user_id}), **params)


def firebase_tokens_list_url():
    return reverse("firebase-tokens-list")


def firebase_tokens_detail_url(token_id):
    return reverse("firebase-tokens-detail", kwargs={"pk": token_id})


def firebase_tokens_delete_by_token_url():
    return reverse("firebase-tokens-delete-by-token")


def returned_ids(response):
    payload = response.data
    if isinstance(payload, dict) and "results" in payload:
        return {item["id"] for item in payload["results"]}
    return {item["id"] for item in payload}


def user_ref(user):
    if user is None:
        return None
    return {
        "id": user.id,
        "name": user.name,
        "phone_number": user.phone_number,
        "role": user.role,
    }
