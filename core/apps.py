from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Auto-load master_seed.json after `migrate` when the DB is empty,
        # so a freshly cloned machine mirrors the source data. See
        # core/signals.py for the (non-destructive, empty-DB-only) logic.
        from django.db.models.signals import post_migrate

        from core.signals import load_seed_on_fresh_db

        post_migrate.connect(
            load_seed_on_fresh_db,
            sender=self,
            dispatch_uid="core.auto_seed_on_fresh_db",
        )
