"""Test helpers for models built on `AbstractBaseModel` (soft delete)."""


def assert_soft_deleted(model, pk):
    """The row is hidden from `objects` but still stored with `deleted_at` set."""
    assert not model.objects.filter(pk=pk).exists()
    row = model.all_objects.get(pk=pk)
    assert row.deleted_at is not None
    return row


def listed_ids(response):
    """Ids in a list response, paginated or not."""
    payload = response.data
    if isinstance(payload, dict) and "results" in payload:
        payload = payload["results"]
    return {item["id"] for item in payload}
