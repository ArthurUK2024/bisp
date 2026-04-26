"""Phase 2 Wave 2 — Profile auto-creation signal.

Every newly-created User row must have a matching Profile row, created by
a post_save signal on User inside the request transaction. The signal is
the single source of truth for "User without Profile is an impossible
state" — if it ever breaks, `user.profile` starts raising
`Profile.DoesNotExist` at arbitrary later call sites and the whole app
melts. These tests pin the invariant so a future refactor cannot quietly
remove it.

The third test exercises the ATOMIC_REQUESTS guarantee: if the post_save
receiver raises inside a transaction, the User insert rolls back in the
same atomic block and no partial state survives.
"""

from unittest.mock import patch

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.factories import UserFactory
from apps.accounts.models import Profile, User

pytestmark = pytest.mark.django_db


def test_creating_user_creates_profile():
    user = UserFactory(email="alice@example.test")
    assert hasattr(user, "profile")
    assert isinstance(user.profile, Profile)


def test_profile_display_name_defaults_to_email_local_part():
    user = UserFactory(email="alice@example.test")
    assert user.profile.display_name == "alice"


def test_profile_one_to_one_constraint():
    user = UserFactory(email="alice@example.test")
    with pytest.raises(IntegrityError), transaction.atomic():
        Profile.objects.create(user=user, display_name="duplicate")


def test_profile_fields_default_to_blank():
    user = UserFactory(email="bob@example.test")
    assert user.profile.phone == ""
    assert user.profile.bio == ""
    assert not user.profile.avatar  # unbound ImageField is falsy


def test_signal_does_not_fire_on_user_update():
    """Re-saving an existing User must NOT create a second Profile row."""
    user = UserFactory(email="alice@example.test")
    original_profile_pk = user.profile.pk
    user.first_name = "Updated"
    user.save()
    user.refresh_from_db()
    assert user.profile.pk == original_profile_pk
    assert Profile.objects.filter(user=user).count() == 1


def test_transaction_rollback_also_rolls_profile():
    """If Profile.objects.create raises inside the atomic block, the User
    insert rolls back in the same block. Proves the ATOMIC_REQUESTS
    guarantee from 02-01 holds at the signal layer."""
    with (
        patch(
            "apps.accounts.signals.Profile.objects.create",
            side_effect=RuntimeError("boom"),
        ),
        pytest.raises(RuntimeError),
        transaction.atomic(),
    ):
        User.objects.create_user(
            email="ghost@example.test",
            password="zx7mnp45",
        )
    # The outer transaction rolled back — neither the User nor any Profile
    # survived.
    assert not User.objects.filter(email="ghost@example.test").exists()
    assert not Profile.objects.filter(user__email="ghost@example.test").exists()
