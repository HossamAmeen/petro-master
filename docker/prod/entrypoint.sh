#!/bin/sh
set -eu

wait_for() {
    host="$1"
    port="$2"
    echo "Waiting for ${host}:${port}..."
    while ! nc -z "$host" "$port"; do
        sleep 1
    done
    echo "${host}:${port} is up"
}

if [ "${SKIP_WAIT:-false}" != "true" ]; then
    wait_for "${DB_HOST:-db}" "${DB_PORT:-5432}"
    wait_for "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}"
fi

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    python manage.py migrate --noinput
fi

exec "$@"
