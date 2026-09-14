#!/usr/bin/env bash
# Restart the Petro Master staging Gunicorn service, plus its Celery worker when
# installed, and show their status.
set -euo pipefail

SERVICE_NAME="petromaster-staging"
WORKER_SERVICE_NAME="${SERVICE_NAME}-celery"

SERVICES=("$SERVICE_NAME")
# The worker is optional (only needed with USE_CELERY=true). Restart it with the
# API when installed so it never runs old task code after a deploy.
if [ "$(systemctl show -p LoadState --value "$WORKER_SERVICE_NAME")" = "loaded" ]; then
  SERVICES+=("$WORKER_SERVICE_NAME")
fi

sudo systemctl restart "${SERVICES[@]}"
sudo systemctl --no-pager --full status "${SERVICES[@]}"
