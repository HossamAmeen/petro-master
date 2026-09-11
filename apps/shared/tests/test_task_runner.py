from unittest.mock import MagicMock

import pytest
from django.db import transaction
from kombu.exceptions import OperationalError

from apps.shared.task_runner import run_task

pytestmark = [pytest.mark.django_db]


class TestRunTask:
    def setup_method(self):
        self.task = MagicMock()
        self.task.name = "apps.example.tasks.example_task"

    def test_runs_inline_when_celery_disabled_success(self, settings):
        settings.USE_CELERY = False

        run_task(self.task, "hello", receiver="01000000000")

        self.task.assert_called_once_with("hello", receiver="01000000000")
        self.task.delay.assert_not_called()

    def test_inline_error_reaches_the_caller_fail(self, settings):
        settings.USE_CELERY = False
        self.task.side_effect = ValueError("provider down")

        with pytest.raises(ValueError, match="provider down"):
            run_task(self.task, "hello")

    def test_queues_on_celery_after_commit_when_enabled_success(
        self, settings, django_capture_on_commit_callbacks
    ):
        settings.USE_CELERY = True

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            run_task(self.task, "hello", receiver="01000000000")

        assert len(callbacks) == 1
        self.task.delay.assert_called_once_with("hello", receiver="01000000000")
        self.task.assert_not_called()

    def test_rolled_back_transaction_queues_nothing_success(
        self, settings, django_capture_on_commit_callbacks
    ):
        settings.USE_CELERY = True

        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            with pytest.raises(RuntimeError):
                with transaction.atomic():
                    run_task(self.task, "hello")
                    raise RuntimeError("rolled back")

        assert callbacks == []
        self.task.delay.assert_not_called()

    def test_queue_failure_is_logged_not_raised_fail(
        self, settings, caplog, django_capture_on_commit_callbacks
    ):
        settings.USE_CELERY = True
        self.task.delay.side_effect = OperationalError("broker down")

        with django_capture_on_commit_callbacks(execute=True):
            run_task(self.task, "hello")

        assert "Failed to queue Celery task apps.example.tasks.example_task" in (
            caplog.text
        )
