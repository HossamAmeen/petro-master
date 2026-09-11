"""`process_ai_operations` reads fuel-gauge photos into `AIApiResponse` rows."""

import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from apps.companies.models.ai_api_response_model import AIApiResponse
from apps.companies.models.operation_model import CarOperation
from apps.users.models import User

pytestmark = [pytest.mark.django_db, pytest.mark.feature]

COMMAND = "apps.companies.management.commands.process_ai_operations"


def fake_completion(number="20"):
    return SimpleNamespace(
        usage=SimpleNamespace(total_tokens=42),
        choices=[SimpleNamespace(message=SimpleNamespace(content=number))],
        model="gpt-4o",
        model_dump_json=lambda: json.dumps({"id": "resp", "number": number}),
    )


class TestProcessAiOperations:
    @pytest.fixture(autouse=True)
    def setup(self, settings, admin_user, car_operation_factory):
        settings.OPENAI_API_KEY = "test-key"
        # the command stamps every row with this specific operator account
        User.objects.create(
            name="AI Operator",
            phone_number="01010079798",
            email="ai-operator@example.com",
            role=User.UserRoles.Admin,
        )
        self.make_operation = car_operation_factory

    def completed_op(self, **overrides):
        overrides.setdefault("status", CarOperation.OperationStatus.COMPLETED)
        overrides.setdefault("amount", Decimal("20.00"))
        overrides.setdefault("fuel_image", "fuel_images/photo.png")
        return self.make_operation(**overrides)

    def run(self, limit, completion=None):
        completion = completion or fake_completion()
        client = MagicMock()
        client.chat.completions.create.return_value = completion
        with patch(f"{COMMAND}.OpenAI", return_value=client) as openai, patch(
            f"{COMMAND}.requests.get"
        ) as get:
            get.return_value = MagicMock(
                content=b"imagebytes", headers={"Content-Type": "image/png"}
            )
            get.return_value.raise_for_status.return_value = None
            call_command("process_ai_operations", limit)
        return client, openai, get

    def test_one_response_per_operation_success(self):
        operations = [self.completed_op() for _ in range(3)]

        client, _, get = self.run(5)

        assert AIApiResponse.objects.count() == 3
        assert client.chat.completions.create.call_count == 3
        assert get.call_count == 3
        for operation in operations:
            response = AIApiResponse.objects.get(car_operation=operation)
            assert response.extracted_number == "20"
            assert response.match_score == 100  # extracted 20 == amount 20
            assert response.token_taken == 42
            assert response.created_by.phone_number == "01010079798"

    def test_match_score_reflects_the_gap_success(self):
        operation = self.completed_op(amount=Decimal("30.00"))

        self.run(1, completion=fake_completion("20"))

        response = AIApiResponse.objects.get(car_operation=operation)
        assert response.extracted_number == "20"
        assert response.match_score == 0  # |20 - 30| = 10

    def test_branch_cap_stops_at_the_limit_success(self):
        for _ in range(3):
            self.completed_op()

        with patch(f"{COMMAND}.Command.MAX_RESPONSES_PER_BRANCH", 2):
            self.run(5)

        # only two rows fit under the per-branch cap
        assert AIApiResponse.objects.count() == 2

    def test_operations_without_a_photo_are_skipped_success(self):
        with_photo = self.completed_op()
        self.completed_op(fuel_image="")

        client, _, _ = self.run(5)

        assert AIApiResponse.objects.count() == 1
        assert AIApiResponse.objects.get().car_operation_id == with_photo.id

    def test_already_processed_operations_are_not_redone_success(self):
        operation = self.completed_op()
        self.run(5)

        self.run(5)

        assert AIApiResponse.objects.filter(car_operation=operation).count() == 1

    def test_missing_api_key_stops_the_command_fail(self, settings):
        from django.core.management.base import CommandError

        settings.OPENAI_API_KEY = ""
        self.completed_op()

        with patch(f"{COMMAND}.os.getenv", return_value=None), pytest.raises(
            CommandError
        ):
            call_command("process_ai_operations", 1)

        assert not AIApiResponse.objects.exists()
