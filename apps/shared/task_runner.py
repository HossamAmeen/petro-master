import logging
from functools import partial
from typing import Any

from celery import Task
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)


def run_task(task: Task, *args: Any, **kwargs: Any) -> None:
    """Run a Celery task on a worker when ``USE_CELERY`` is on, otherwise inline.

    On Celery the task is queued once the current transaction commits, so nothing
    goes out for work that rolls back. Arguments must be JSON-serializable.

    Inline it runs right away in this process, the same as calling the function
    directly: one attempt, no retries, and exceptions reach the caller.
    """
    if settings.USE_CELERY:
        transaction.on_commit(partial(_enqueue, task, args, kwargs))
    else:
        task(*args, **kwargs)


def _enqueue(task: Task, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
    # Log instead of raising: the caller's changes are already committed, and
    # failing the request now would only invite a retry of work that happened.
    try:
        task.delay(*args, **kwargs)
    except Exception:
        logger.exception("Failed to queue Celery task %s", task.name)
