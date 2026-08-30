#!/usr/bin/env bash
# Follow live Gunicorn access and error logs for the staging API.
set -euo pipefail

exec sudo journalctl -fu petromaster-staging -o cat
