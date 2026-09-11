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

## Celery worker

```bash
celery -A config worker --loglevel=info
celery -A config worker --loglevel=info --purge
```

## Celery beat

```bash
celery -A config beat --loglevel=info
```
