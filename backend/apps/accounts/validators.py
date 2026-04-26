"""Password validators for accounts.

LetterAndDigitValidator enforces AUTH-01's rule: at least eight characters
with at least one letter and one digit. Django's MinimumLengthValidator
already covers the length rule when configured, but this validator is the
one authoritative place that also enforces the letter-plus-digit rule. It
is listed AFTER the four Django defaults in ``AUTH_PASSWORD_VALIDATORS`` so
the built-ins run first. The serializer layer in Plan 02-02 calls
``django.contrib.auth.password_validation.validate_password()`` which walks
the whole chain.
"""

from django.core.exceptions import ValidationError


class LetterAndDigitValidator:
    """Reject passwords that are too short, letters-only, or digits-only."""

    def __init__(self, min_length: int = 8) -> None:
        self.min_length = min_length

    def validate(self, password: str, user=None) -> None:
        if len(password) < self.min_length:
            raise ValidationError(
                f"Password must be at least {self.min_length} characters long.",
                code="password_too_short",
            )
        if not any(ch.isalpha() for ch in password):
            raise ValidationError(
                "Password must contain at least one letter.",
                code="password_no_letter",
            )
        if not any(ch.isdigit() for ch in password):
            raise ValidationError(
                "Password must contain at least one digit.",
                code="password_no_digit",
            )

    def get_help_text(self) -> str:
        return (
            f"Your password must be at least {self.min_length} characters "
            "long and contain at least one letter and one digit."
        )
