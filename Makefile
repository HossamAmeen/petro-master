.PHONY: run migrate makemigrations shell format lint check test test-features coverage coverage-api process_ai restart stop

-include .env

SERVICE_NAME ?= petromaster-staging
WORKER_SERVICE_NAME ?= $(SERVICE_NAME)-celery
# The worker is optional (only needed with USE_CELERY=true); manage it with the
# API only once its unit is installed (see deploy/celery-worker.service).
SERVICES = $(SERVICE_NAME) $(if $(filter loaded,$(shell systemctl show -p LoadState --value $(WORKER_SERVICE_NAME) 2>/dev/null)),$(WORKER_SERVICE_NAME))

run:
	python3 manage.py runserver

# Runs the background tasks queued when USE_CELERY=true.
worker:
	python3 -m celery -A config worker --loglevel=info

migrate:
	python3 manage.py migrate

makemigrations:
	python3 manage.py makemigrations

shell:
	python3 manage.py shell

format:
	python3 -m isort .
	python3 -m black .

lint:
	python3 -m flake8

# Same tools without writing anything; fails if a file needs formatting (CI).
check:
	python3 -m isort --check-only --diff .
	python3 -m black --check --diff .
	python3 -m flake8

test:
	python3 -m pytest

# End-to-end business scenarios only (tests/features, `feature` marker).
test-features:
	python3 -m pytest -m feature

# Run the whole suite and report code coverage (config in pyproject.toml).
# Writes a term summary plus an htmlcov/ report; fails under 80%.
coverage:
	python3 -m pytest --cov --cov-report=term-missing --cov-report=html --cov-fail-under=80

# The API layer (views, serializers, permissions, filters and the shared
# helpers they use) must stay fully covered, statements and branches.
API_COVERAGE_INCLUDE = apps/*/api/*,apps/*/v1/*,apps/shared/*,apps/stations/filters.py,configrations/*

coverage-api:
	python3 -m pytest --cov --cov-report=
	python3 -m coverage report --include="$(API_COVERAGE_INCLUDE)" --show-missing --skip-covered --fail-under=100

limit ?= 1

ifeq (process_ai,$(firstword $(MAKECMDGOALS)))
  PROCESS_AI_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(PROCESS_AI_ARGS),)
    limit = $(PROCESS_AI_ARGS)
    $(eval $(PROCESS_AI_ARGS):;@:)
  endif
endif

process_ai:
	python3 manage.py process_ai_operations $(limit)

restart:
	sudo systemctl restart $(SERVICES)
	sudo systemctl --no-pager --full status $(SERVICES)

stop:
	sudo systemctl stop $(SERVICES)
	sudo systemctl --no-pager --full status $(SERVICES)