"""PROF-04 backend half — public profile endpoint tests.

Covers GET /api/v1/users/<id>/ as an AllowAny endpoint. The response
shape must contain no email, no phone, and no password hash — the
private surface of the User model is unreachable by construction via
PublicProfileSerializer's positive field list.
"""

import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_public_profile_returns_safe_shape(api_client):
    user = UserFactory(email="alice@example.test")
    user.profile.display_name = "Alice"
    user.profile.bio = "Rents out a drill."
    user.profile.save()

    response = api_client.get(
        reverse("public-profile", kwargs={"id": user.id}),
    )

    assert response.status_code == 200
    assert set(response.data.keys()) == {
        "id",
        "display_name",
        "bio",
        "avatar",
        "date_joined",
    }
    assert response.data["id"] == user.id
    assert response.data["display_name"] == "Alice"
    assert response.data["bio"] == "Rents out a drill."


def test_public_profile_omits_email_and_phone(api_client):
    user = UserFactory(email="alice@example.test")
    user.profile.phone = "+998 90 123 4567"
    user.profile.save()

    response = api_client.get(
        reverse("public-profile", kwargs={"id": user.id}),
    )

    assert response.status_code == 200
    assert "email" not in response.data
    assert "phone" not in response.data
    assert "password" not in response.data
    raw = str(response.data)
    assert "alice@example.test" not in raw
    assert "+998" not in raw
    assert "pbkdf2" not in raw


def test_public_profile_404_on_nonexistent_user(api_client):
    response = api_client.get(
        reverse("public-profile", kwargs={"id": 99999999}),
    )
    assert response.status_code == 404


def test_public_profile_404_on_inactive_user(api_client):
    user = UserFactory(email="inactive@example.test", is_active=False)
    response = api_client.get(
        reverse("public-profile", kwargs={"id": user.id}),
    )
    assert response.status_code == 404


def test_public_profile_does_not_require_auth(api_client):
    """Anonymous callers get a 200, not a 401 — this endpoint is AllowAny."""
    user = UserFactory(email="public@example.test")
    response = api_client.get(
        reverse("public-profile", kwargs={"id": user.id}),
    )
    assert response.status_code == 200
