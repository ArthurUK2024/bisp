"""Accounts models — User, UserManager, and Profile.

Phase 1 defined User with email as USERNAME_FIELD so Phase 2 could add JWT
auth without a migration rewrite. Phase 2 Wave 2 adds Profile as a 1:1
satellite to keep auth concerns (password hash, permissions, last_login)
separate from display concerns (display_name, phone, bio, avatar).

Profile is created by a post_save signal on User (see signals.py) so every
User row has a matching Profile row from row-zero and ``user.profile``
never raises ``Profile.DoesNotExist`` at runtime. The signal fires inside
the request transaction (ATOMIC_REQUESTS=True in settings.py), so a failed
Profile insert rolls the User insert back in the same atomic block.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager that uses email as the unique identifier instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user with email as the unique identifier."""

    username = None
    email = models.EmailField("email address", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Profile(models.Model):
    """Display-layer user profile, created by a post_save signal on User.

    PROF-01 covers display_name / phone / bio read+write through the
    /users/me/profile/ endpoint; PROF-02 covers avatar upload through the
    /users/me/avatar/ endpoint. PROF-04 reads this model's shape back out
    through PublicProfileSerializer for the /users/<id>/ public page.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=80, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    avatar = models.ImageField(upload_to="avatars/%Y/%m/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile({self.user.email})"
