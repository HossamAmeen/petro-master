from unittest.mock import MagicMock, patch

from apps.shared.generate_code import generate_unique_code


def fake_model(exists_results):
    model = MagicMock()
    model.objects.filter.return_value.exists.side_effect = exists_results
    return model


class TestGenerateUniqueCode:

    @patch("apps.shared.generate_code.random.randint", return_value=123456)
    def test_returns_code_when_unused_success(self, randint):
        model = fake_model([False])

        code = generate_unique_code(model)

        assert code == "123456"
        randint.assert_called_once_with(100000, 999999)
        model.objects.filter.assert_called_once_with(code="123456")

    @patch("apps.shared.generate_code.random.randint", side_effect=[111111, 222222])
    def test_retries_until_code_is_unused_success(self, randint):
        model = fake_model([True, False])

        code = generate_unique_code(model, look_up="otp", min_value=1, max_value=9)

        assert code == "222222"
        assert randint.call_count == 2
        model.objects.filter.assert_any_call(otp="111111")
        model.objects.filter.assert_called_with(otp="222222")
