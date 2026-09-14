.PHONY: run migrate makemigrations shell format lint check process_ai restart stop

-include .env

SERVICE_NAME ?= petromaster-staging

run:
	python3 manage.py runserver

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
	sudo systemctl restart $(SERVICE_NAME)
	sudo systemctl --no-pager --full status $(SERVICE_NAME)

stop:
	sudo systemctl stop $(SERVICE_NAME)
	sudo systemctl --no-pager --full status $(SERVICE_NAME)