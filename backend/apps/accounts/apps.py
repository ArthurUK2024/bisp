"""Accounts app config."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self) -> None:
        # Import here — not at module top — so Django's app loader has a
        # chance to register the models before the signal receiver binds
        # to them. This is Django's sanctioned signal wiring pattern.
        from . import signals  # noqa: F401
