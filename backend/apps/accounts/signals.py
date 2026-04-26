"""Post-save signal wiring for the accounts app.

Every newly-created User row gets a matching Profile row created inside
the same transaction. The receiver is wired in AccountsConfig.ready() so
it fires as soon as Django's app loader finishes registering models.

ATOMIC_REQUESTS=True (settings.DATABASES[default]) wraps every request in
a transaction, so if the Profile insert raises inside the signal the
enclosing User insert rolls back in the same atomic block. Exercised by
test_transaction_rollback_also_rolls_profile.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """Auto-create a Profile for every new User. No-op on update."""
    if not created:
        return
    default_display = instance.email.split("@")[0] if instance.email else ""
    Profile.objects.create(
        user=instance,
        display_name=default_display,
    )
