from config.settings import *  # noqa: F401, F403

# Test settings
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Tests never need a broker, whatever .env says: tasks run inline, and a test
# that turns USE_CELERY on runs the queued task in-process the way a worker
# would (retries included, errors kept out of the caller).
USE_CELERY = False
CELERY_TASK_ALWAYS_EAGER = True
