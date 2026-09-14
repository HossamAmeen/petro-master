from types import SimpleNamespace
from unittest.mock import MagicMock

from apps.shared.mixins.inject_user_mixins import (
    InjectCompanyUserMixin,
    InjectUserMixin,
)


def view_with(mixin, **request_attrs):
    view = mixin()
    view.request = SimpleNamespace(user="request-user", **request_attrs)
    return view


class TestInjectUserMixin:

    def test_perform_create_sets_created_by_success(self):
        serializer = MagicMock()

        view_with(InjectUserMixin).perform_create(serializer)

        serializer.save.assert_called_once_with(created_by="request-user")

    def test_perform_update_sets_updated_by_success(self):
        serializer = MagicMock()

        view_with(InjectUserMixin).perform_update(serializer)

        serializer.save.assert_called_once_with(updated_by="request-user")


class TestInjectCompanyUserMixin:

    def test_perform_create_sets_company_and_created_by_success(self):
        serializer = MagicMock()

        result = view_with(InjectCompanyUserMixin, company_id=7).perform_create(
            serializer
        )

        serializer.save.assert_called_once_with(company_id=7, created_by="request-user")
        assert result is serializer.save.return_value

    def test_perform_update_sets_updated_by_success(self):
        serializer = MagicMock()

        result = view_with(InjectCompanyUserMixin, company_id=7).perform_update(
            serializer
        )

        serializer.save.assert_called_once_with(updated_by="request-user")
        assert result is serializer.save.return_value
