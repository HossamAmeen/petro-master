#!/usr/bin/env bash
# Manage the Petro Master production Gunicorn service, plus its Celery worker
# when installed.
set -euo pipefail

SERVICE_NAME="petromaster-staging"
WORKER_SERVICE_NAME="${SERVICE_NAME}-celery"
ACTION="${1:-status}"

SERVICES=("$SERVICE_NAME")
# The worker is optional (only needed with USE_CELERY=true).
if [ "$(systemctl show -p LoadState --value "$WORKER_SERVICE_NAME")" = "loaded" ]; then
  SERVICES+=("$WORKER_SERVICE_NAME")
fi

case "$ACTION" in
  start|stop|restart|status)
    exec sudo systemctl "$ACTION" "${SERVICES[@]}"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
