"""AUTH-02/03 — refresh endpoint rotates cookie and blacklists old token.

These tests exercise the full rotation path: login seeds a refresh
cookie, the first /refresh/ call reads it and rotates it (new cookie,
new value), and a subsequent /refresh/ with the OLD value must fail
because BLACKLIST_AFTER_ROTATION is on.
"""

import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def _login(api_client, email: str = "alice@example.test", password: str = "zx7mnp45"):
    user = UserFactory(email=email)
    user.set_password(password)
    user.save()
    response = api_client.post(
        reverse("login"),
        {"email": email, "password": password},
        format="json",
    )
    assert response.status_code == 200, response.data
    return response, user


def test_refresh_reads_cookie_returns_new_access(api_client):
    _login(api_client)
    # APIClient carries cookies forward between calls on the same instance.
    refresh_response = api_client.post(reverse("refresh"), {}, format="json")
    assert refresh_response.status_code == 200
    assert "access" in refresh_response.data


def test_refresh_rotates_cookie(api_client):
    login_response, _ = _login(api_client)
    old_cookie = login_response.cookies["refresh_token"].value
    refresh_response = api_client.post(reverse("refresh"), {}, format="json")
    assert refresh_response.status_code == 200
    new_cookie = refresh_response.cookies["refresh_token"].value
    assert new_cookie
    assert new_cookie != old_cookie


def test_refresh_blacklists_old_token_after_rotation(api_client):
    login_response, _ = _login(api_client)
    old_cookie = login_response.cookies["refresh_token"].value
    # First rotation: old blacklisted, new cookie set on the client.
    first = api_client.post(reverse("refresh"), {}, format="json")
    assert first.status_code == 200
    # Force the old cookie back onto the client and try again.
    api_client.cookies["refresh_token"] = old_cookie
    second = api_client.post(reverse("refresh"), {}, format="json")
    assert second.status_code == 401


def test_refresh_without_cookie_returns_401(api_client):
    response = api_client.post(reverse("refresh"), {}, format="json")
    assert response.status_code == 401


def test_refresh_does_not_leak_refresh_in_body(api_client):
    _login(api_client)
    refresh_response = api_client.post(reverse("refresh"), {}, format="json")
    assert "refresh" not in refresh_response.data
