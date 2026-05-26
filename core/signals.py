"""``post_migrate`` hook: auto-load ``master_seed.json`` into a *fresh* database.

Goal: when the project is cloned onto another machine, running

    poetry run python manage.py migrate

should not only build the schema but also bring across the data, so the new
machine mirrors the source.

To stay safe, the seed is loaded **only when the database is empty**
(detected by "there are no users yet"). On any database that already has
data this is a no-op — existing rows are never deleted or overwritten. This
means it is harmless to run ``migrate`` repeatedly on the dev machine: the
fixture is replayed exactly once, on the very first migrate of a blank DB.

Opt out at any time with the env var ``DISABLE_AUTO_SEED=1`` (e.g. in CI).

For an explicit, *destructive* re-sync (wipe seed tables and reload), use the
``data_load`` management command instead — that is the deliberate, manual path.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from django.conf import settings
from django.core import management
from django.db import DEFAULT_DB_ALIAS

SEED_PATH = (
    Path(settings.BASE_DIR) / "core" / "fixtures" / "master_seed.json"
)


def load_seed_on_fresh_db(sender, using=DEFAULT_DB_ALIAS, verbosity=1, **kwargs):
    """Load the seed fixture if (and only if) this is a brand-new, empty DB."""
    # `core_user` is just an alias to the same physical DB as `default`; only
    # act on the real default connection so we never load twice.
    if using != DEFAULT_DB_ALIAS:
        return

    # Never auto-seed while running the test suite (a fresh test DB would
    # otherwise pull in the whole fixture on every run).
    if "test" in sys.argv:
        return

    if os.getenv("DISABLE_AUTO_SEED") == "1":
        return

    if not SEED_PATH.exists():
        return

    # "Fresh" == no users. If anyone exists we assume the DB is already
    # populated and leave it completely untouched.
    from core.models import User

    if User.objects.using(using).exists():
        return

    if verbosity:
        print(f"[auto-seed] Empty database detected — loading {SEED_PATH.name} ...")
    management.call_command(
        "loaddata", str(SEED_PATH), database=using, verbosity=verbosity
    )
    if verbosity:
        print("[auto-seed] Seed loaded.")
