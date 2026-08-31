.PHONY: run migrate makemigrations shell process_ai restart stop

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