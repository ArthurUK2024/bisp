"""AUTH-02 — login endpoint tests.

Cookie attribute expectations mirror the single source of truth in
``apps.accounts.views._set_refresh_cookie``. The ``Secure`` attribute
tracks ``DEBUG``: True when Django is in production posture, False in
dev so the browser will accept the cookie over ``http://localhost``.
The rest of the attributes are invariant across environments.
"""

import pytest
from django.conf import settings
from django.urls import reverse

from apps.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def _seed_user(email: str = "alice@example.test", password: str = "zx7mnp45"):
    user = UserFactory(email=email)
    user.set_password(password)
    user.save()
    return user


def test_login_returns_access_and_sets_cookie(api_client):
    _seed_user()
    response = api_client.post(
        reverse("login"),
        {"email": "alice@example.test", "password": "zx7mnp45"},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh_token" in response.cookies


def test_login_cookie_attributes(api_client):
    _seed_user()
    response = api_client.post(
        reverse("login"),
        {"email": "alice@example.test", "password": "zx7mnp45"},
        format="json",
    )
    cookie = response.cookies["refresh_token"]
    # HttpOnly is always on — the refresh token must never be reachable
    # from JavaScript.
    assert cookie["httponly"] is True
    # Secure flips with DEBUG: True in production posture, False in the
    # local dev loop so the browser still accepts the cookie over http.
    expected_secure = not settings.DEBUG
    assert bool(cookie["secure"]) is expected_secure
    assert cookie["samesite"] == "Lax"
    assert cookie["path"] == "/api/v1/auth/"
    assert int(cookie["max-age"]) == 7 * 24 * 3600


def test_login_does_not_leak_refresh_in_body(api_client):
    _seed_user()
    response = api_client.post(
        reverse("login"),
        {"email": "alice@example.test", "password": "zx7mnp45"},
        format="json",
    )
    assert "refresh" not in response.data
    # Defensive: the raw string form must not contain the refresh cookie value.
    cookie_value = response.cookies["refresh_token"].value
    assert cookie_value not in str(response.data)


def test_login_bad_credentials_returns_401(api_client):
    _seed_user()
    response = api_client.post(
        reverse("login"),
        {"email": "alice@example.test", "password": "wrongpass"},
        format="json",
    )
    assert response.status_code == 401
