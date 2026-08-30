#!/usr/bin/env bash
# Restart the Petro Master staging Gunicorn service and show its status.
set -euo pipefail

SERVICE_NAME="petromaster-staging"

sudo systemctl restart "$SERVICE_NAME"
sudo systemctl --no-pager --full status "$SERVICE_NAME"
