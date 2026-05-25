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
