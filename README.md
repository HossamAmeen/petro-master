# petro-master

## Dependency versions

| Component | Version (from `requirements/base.txt`) |
| --- | --- |
| Django | `4.2` |
| Django REST Framework | `3.15.2` |
| Gunicorn | `23.0.0` |

Python is not pinned in this repository; Django 4.2 officially supports Python 3.8–3.12. Use whichever of those fits your deployment (commonly 3.10–3.12).

## Run the development server

```bash
python manage.py runserver
```

## Format and lint

Install the dev tools with `pip install -r requirements/dev.txt`, then with the venv active:

```bash
make format   # isort + black, rewrites files
make lint     # flake8
make check    # all three without writing; fails if anything needs fixing (CI)
```

black and isort read `pyproject.toml`; flake8 reads `.flake8`. Migrations, `venv`, and `settings.py` are excluded from all three. `.pre-commit-config.yaml` pins the same versions as `requirements/dev.txt` — bump both together.

## Run with Gunicorn

```bash
gunicorn config.wsgi:application -b 0.0.0.0:8001 --log-level debug -w 1
```

## Background tasks (Celery)

Push notifications, SMS, and emails are Celery tasks, started with `run_task` (`apps/shared/task_runner.py`). `USE_CELERY` in `.env` picks where they run:

- `USE_CELERY=false` (default): inline, inside the request. No Redis or worker needed.
- `USE_CELERY=true`: queued on Redis (`CELERY_BROKER_URL`) once the DB transaction commits, then run by a worker, which retries SMS and email on network errors.

Start a worker before turning it on:

```bash
make worker   # celery -A config worker --loglevel=info
celery -A config worker --loglevel=info --purge
```

For deployment, install `deploy/celery-worker.service` (instructions at the top of the file). Once installed, `make restart` / `make stop` and the scripts in `deploy/` restart the worker along with the API.

## Celery beat

```bash
celery -A config beat --loglevel=info
```
