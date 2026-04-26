"""AUTH-04 — logout blacklists refresh and clears cookie.

Logout is the only auth endpoint that requires an access-token
Authorization header in addition to the refresh cookie. Without
IsAuthenticated the endpoint would be a trivial DoS vector: anyone
could post anything and trigger a blacklist write per request.
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


def test_logout_requires_auth(api_client):
    response = api_client.post(reverse("logout"))
    assert response.status_code == 401


def test_logout_blacklists_refresh(api_client):
    login, _ = _login(api_client)
    access = login.data["access"]
    old_refresh = login.cookies["refresh_token"].value
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    response = api_client.post(reverse("logout"))
    assert response.status_code == 204
    # Reusing the old refresh token must fail after blacklist.
    api_client.credentials()
    api_client.cookies["refresh_token"] = old_refresh
    refresh_response = api_client.post(reverse("refresh"), {}, format="json")
    assert refresh_response.status_code == 401


def test_logout_clears_cookie(api_client):
    login, _ = _login(api_client)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    response = api_client.post(reverse("logout"))
    assert response.status_code == 204
    cookie = response.cookies["refresh_token"]
    # Django's delete_cookie sets Max-Age=0 (and an expired date).
    assert int(cookie["max-age"]) == 0 or cookie.value == ""
