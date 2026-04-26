"""Phase 2 Wave 0 pin: lock the SimpleJWT config so later plans cannot drift it.

Ten tests cover the four SIMPLE_JWT dict values, the ``token_blacklist``
install-apps entry, the ``LetterAndDigitValidator`` wiring, and the
validator's four behavioural branches (short / letters-only / digits-only /
mixed). Plans 02-02 through 02-06 depend on every one of these invariants.
"""

from datetime import timedelta

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.accounts.validators import LetterAndDigitValidator


def test_access_token_lifetime_is_five_minutes():
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=5)


def test_refresh_token_lifetime_is_seven_days():
    assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] == timedelta(days=7)


def test_rotate_refresh_tokens_enabled():
    assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True


def test_blacklist_after_rotation_enabled():
    assert settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"] is True


def test_token_blacklist_app_installed():
    assert "rest_framework_simplejwt.token_blacklist" in settings.INSTALLED_APPS


def test_letter_and_digit_validator_installed():
    names = [v["NAME"] for v in settings.AUTH_PASSWORD_VALIDATORS]
    assert "apps.accounts.validators.LetterAndDigitValidator" in names


def test_letter_and_digit_validator_rejects_letters_only():
    with pytest.raises(ValidationError):
        LetterAndDigitValidator().validate("abcdefgh")


def test_letter_and_digit_validator_rejects_digits_only():
    with pytest.raises(ValidationError):
        LetterAndDigitValidator().validate("12345678")


def test_letter_and_digit_validator_rejects_short():
    with pytest.raises(ValidationError):
        LetterAndDigitValidator().validate("abc1")


def test_letter_and_digit_validator_accepts_mixed():
    LetterAndDigitValidator().validate("abcdef12")
