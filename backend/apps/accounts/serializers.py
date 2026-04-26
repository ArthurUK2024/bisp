"""DRF serializers for the accounts app — Phase 2 Waves 1 and 2.

Wave 1 (02-02):
    - UserRegistrationSerializer — mirrors AUTH_PASSWORD_VALIDATORS on
      the server side (so the API is the authoritative check; the Zod
      schema in 02-04 is UX-only).
    - UserSerializer — read-only /me/ shape with an explicit positive
      field list so the password hash can never leak.

Wave 2 (02-03):
    - ProfileSerializer — read+write for /users/me/profile/. display_name
      / phone / bio are writable; avatar is read-only and updated via the
      dedicated /users/me/avatar/ endpoint.
    - AvatarUploadSerializer — single-field wrapper for the multipart
      avatar upload.
    - PublicProfileSerializer — PROF-04 public-safe shape for
      /users/<id>/. Composed against the User model with source= on each
      profile field so the response flattens User + Profile into one
      payload. Positive field list — no email, no phone, no password.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Profile

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = ["id", "email", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists.",
            )
        return value

    def validate_password(self, value: str) -> str:
        # Walks the full AUTH_PASSWORD_VALIDATORS chain set in settings.py
        # including LetterAndDigitValidator from 02-01.
        validate_password(value)
        return value

    def create(self, validated_data: dict):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )


class UserSerializer(serializers.ModelSerializer):
    """Read-only user shape for /me/. Explicit positive field list — no __all__."""

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "is_staff"]
        read_only_fields = fields


class ProfileSerializer(serializers.ModelSerializer):
    """PROF-01 — read+write shape for /users/me/profile/.

    display_name / phone / bio are writable; avatar is read-only (updated
    through the dedicated /users/me/avatar/ endpoint). Max-length
    validation is redundant with the model's CharField/TextField
    constraints but happens at the serializer layer so the 400 response
    carries a clean field error before the DB constraint raises.
    """

    class Meta:
        model = Profile
        fields = ["display_name", "phone", "bio", "avatar"]
        read_only_fields = ["avatar"]

    def validate_display_name(self, value: str) -> str:
        if len(value) > 80:
            raise serializers.ValidationError(
                "Display name must be at most 80 characters.",
            )
        return value

    def validate_phone(self, value: str) -> str:
        if len(value) > 20:
            raise serializers.ValidationError(
                "Phone must be at most 20 characters.",
            )
        return value

    def validate_bio(self, value: str) -> str:
        if len(value) > 300:
            raise serializers.ValidationError(
                "Bio must be at most 300 characters.",
            )
        return value


class AvatarUploadSerializer(serializers.Serializer):
    """PROF-02 — single-field serializer for the multipart avatar upload.

    The heavy lifting (size check, python-magic sniff, Pillow resize, JPEG
    re-save) lives in services.save_avatar — this serializer only proves
    the upload is a valid image from DRF's perspective and hands the
    file over to the service.
    """

    avatar = serializers.ImageField()


class PublicProfileSerializer(serializers.ModelSerializer):
    """PROF-04 — public-safe shape keyed by User id; no email, no phone.

    Composed against the User model with source= on each profile field
    so the final payload is a flat {id, display_name, bio, avatar,
    date_joined} rather than a nested user/profile structure. The
    positive field list is the single line that prevents the password
    hash and private fields from leaking.
    """

    display_name = serializers.CharField(
        source="profile.display_name",
        read_only=True,
    )
    bio = serializers.CharField(source="profile.bio", read_only=True)
    avatar = serializers.ImageField(
        source="profile.avatar",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = User
        fields = ["id", "display_name", "bio", "avatar", "date_joined"]
        read_only_fields = fields
