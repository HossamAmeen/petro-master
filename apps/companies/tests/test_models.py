import pytest


@pytest.mark.django_db
@pytest.mark.parametrize("fixture_name", ["company", "company_branch"])
def test_company_models_are_available_by_default(request, fixture_name):
    instance = request.getfixturevalue(fixture_name)

    assert instance.is_available is True


@pytest.mark.django_db
@pytest.mark.parametrize("fixture_name", ["company", "company_branch"])
def test_company_models_can_be_made_unavailable(request, fixture_name):
    instance = request.getfixturevalue(fixture_name)

    instance.is_available = False
    instance.save(update_fields=["is_available"])
    instance.refresh_from_db()

    assert instance.is_available is False
