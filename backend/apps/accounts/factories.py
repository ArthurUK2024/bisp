"""factory-boy factories for the accounts app.

UserFactory routes passwords through ``User.objects.create_user`` via a
``_create`` override so the custom UserManager's ``set_password`` hook
runs and passwords are never stored as plaintext. The post_save signal
fires from create_user and auto-creates a Profile for every factory
call, so tests can read ``user.profile`` immediately without boilerplate.

ProfileFactory is the override hook when a test wants to pre-seed the
profile with non-default values (e.g. a known display_name or bio for
a public profile shape assertion). It subclasses DjangoModelFactory on
Profile and ``django_get_or_create`` is keyed on the one-to-one user
relationship so re-calling with the same user idempotently returns
the signal-created Profile.
"""

import factory
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.test")
    is_active = True
    is_staff = False
    is_superuser = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "testpass1")
        return model_class.objects.create_user(password=password, **kwargs)


class ProfileFactory(factory.django.DjangoModelFactory):
    """Override hook for tests that want non-default profile fields.

    The UserFactory's post_save signal already creates a Profile for every
    new user, so ``django_get_or_create=('user',)`` makes this factory
    idempotent: calling ``ProfileFactory(user=existing)`` returns the
    signal-created row instead of raising IntegrityError on the OneToOne
    constraint.
    """

    class Meta:
        model = Profile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    display_name = factory.LazyAttribute(lambda o: o.user.email.split("@")[0])
    phone = ""
    bio = ""
