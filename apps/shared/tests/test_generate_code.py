from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from apps.accounting.models import KhaznaTransaction
from apps.shared.generate_code import generate_unique_code


def fake_model(exists_results):
    model = MagicMock()
    model._base_manager.filter.return_value.exists.side_effect = exists_results
    return model


class TestGenerateUniqueCode:

    @patch("apps.shared.generate_code.random.randint", return_value=123456)
    def test_returns_code_when_unused_success(self, randint):
        model = fake_model([False])

        code = generate_unique_code(model)

        assert code == "123456"
        randint.assert_called_once_with(100000, 999999)
        model._base_manager.filter.assert_called_once_with(code="123456")

    @patch("apps.shared.generate_code.random.randint", side_effect=[111111, 222222])
    def test_retries_until_code_is_unused_success(self, randint):
        model = fake_model([True, False])

        code = generate_unique_code(model, look_up="otp", min_value=1, max_value=9)

        assert code == "222222"
        assert randint.call_count == 2
        model._base_manager.filter.assert_any_call(otp="111111")
        model._base_manager.filter.assert_called_with(otp="222222")


@pytest.mark.django_db
class TestGenerateUniqueCodeSoftDelete:

    @patch("apps.shared.generate_code.random.randint", side_effect=[111111, 222222])
    def test_skips_code_held_by_soft_deleted_row_success(self, randint, admin_user):
        tx = KhaznaTransaction.objects.create(
            amount=Decimal("10.00"), reference_code="111111", created_by=admin_user
        )
        tx.delete()

        code = generate_unique_code(KhaznaTransaction, look_up="reference_code")

        assert code == "222222"
