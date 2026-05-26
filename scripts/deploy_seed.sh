#!/usr/bin/env bash
# deploy_seed.sh — replace the database content with the seed snapshot.
#
# Usage on the server:
#     cd /path/to/tbsmproduction
#     ./scripts/deploy_seed.sh
#
# What it does:
#     1. Activates the project venv (if present at .venv).
#     2. Runs `manage.py migrate` so schema is current.
#     3. Runs `manage.py data_load --no-input` which:
#        - Deletes every row from the seed-managed tables (children first).
#        - Loads `core/fixtures/master_seed.json` into a fresh state.
#
# Pre-requisites:
#     - `.env.local` (or environment variables) must point at the correct
#       database, exactly like local dev does.
#     - `core/fixtures/master_seed.json` must be committed/uploaded.
#
# Safety:
#     - Wraps the destructive step in a single transaction; on failure
#       nothing is committed.
#     - `AuditLogEntry`, `DefectStat`, sessions, and Django internals are
#       NOT touched.
set -euo pipefail

# Move to the project root (script lives in <root>/scripts/)
cd "$(dirname "$0")/.."

if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

echo "==> Running migrations"
python manage.py migrate --no-input

echo "==> Replacing data from seed fixture"
python manage.py data_load --no-input

echo
echo "==> Seed deploy completed."
