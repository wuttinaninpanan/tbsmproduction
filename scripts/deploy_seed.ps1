# deploy_seed.ps1 — Windows PowerShell equivalent of deploy_seed.sh
#
# Usage:
#     cd <project root>
#     .\scripts\deploy_seed.ps1
#
# Replaces the contents of the seed-managed tables with the snapshot in
# core/fixtures/master_seed.json. See deploy_seed.sh for details.

$ErrorActionPreference = "Stop"

# Move to project root (script lives in <root>/scripts/)
Set-Location -Path (Join-Path $PSScriptRoot "..")

if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
}

Write-Host "==> Running migrations"
python manage.py migrate --no-input

Write-Host "==> Replacing data from seed fixture"
python manage.py data_load --no-input

Write-Host ""
Write-Host "==> Seed deploy completed."
