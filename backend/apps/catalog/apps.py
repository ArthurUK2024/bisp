"""Catalog app config."""

from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.catalog"

    def ready(self):
        # Connect the post_save signal that keeps Listing.search_vector
        # fresh on every write.
        from . import signals  # noqa: F401
