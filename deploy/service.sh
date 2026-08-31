#!/usr/bin/env bash
# Manage the Petro Master production Gunicorn service.
set -euo pipefail

SERVICE_NAME="petromaster-staging"
ACTION="${1:-status}"

case "$ACTION" in
  start|stop|restart|status)
    exec sudo systemctl "$ACTION" "$SERVICE_NAME"
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}" >&2
    exit 2
    ;;
esac
