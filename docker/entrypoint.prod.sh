#!/usr/bin/env bash
# Production container entrypoint: prepare the app, then exec the CMD (gunicorn).
set -euo pipefail

echo "==> Applying database migrations"
python manage.py migrate --no-input

echo "==> Collecting static files"
python manage.py collectstatic --no-input --clear

echo "==> Starting: $*"
exec "$@"
