"""PROF-01 — profile edit endpoint tests.

Covers GET /api/v1/users/me/profile/ (authenticated read) and PATCH
against the same URL (authenticated write on display_name / phone / bio).
Field-level max length validation lives in ProfileSerializer — tests
exercise the 400 path at the serializer layer, not the DB constraint.
"""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_get_profile_requires_auth(api_client):
    response = api_client.get(reverse("my-profile"))
    assert response.status_code == 401


def test_get_profile_returns_current_user_profile(authed_client_factory):
    client, user = authed_client_factory()
    response = client.get(reverse("my-profile"))
    assert response.status_code == 200
    assert set(response.data.keys()) == {"display_name", "phone", "bio", "avatar"}
    # The signal populated display_name with the email local part.
    assert response.data["display_name"] == user.email.split("@")[0]
    assert response.data["phone"] == ""
    assert response.data["bio"] == ""
    assert response.data["avatar"] is None


def test_patch_profile_fields(authed_client_factory):
    client, user = authed_client_factory()
    response = client.patch(
        reverse("my-profile"),
        {
            "display_name": "New Name",
            "phone": "+998 90 000 0000",
            "bio": "Hi!",
        },
        format="json",
    )
    assert response.status_code == 200
    user.profile.refresh_from_db()
    assert user.profile.display_name == "New Name"
    assert user.profile.phone == "+998 90 000 0000"
    assert user.profile.bio == "Hi!"


def test_patch_profile_enforces_bio_max_length(authed_client_factory):
    client, _ = authed_client_factory()
    response = client.patch(
        reverse("my-profile"),
        {"bio": "x" * 301},
        format="json",
    )
    assert response.status_code == 400
    assert "bio" in response.data


def test_patch_profile_enforces_display_name_max_length(authed_client_factory):
    client, _ = authed_client_factory()
    response = client.patch(
        reverse("my-profile"),
        {"display_name": "x" * 81},
        format="json",
    )
    assert response.status_code == 400
    assert "display_name" in response.data


def test_patch_profile_enforces_phone_max_length(authed_client_factory):
    client, _ = authed_client_factory()
    response = client.patch(
        reverse("my-profile"),
        {"phone": "+" + "9" * 20},
        format="json",
    )
    assert response.status_code == 400
    assert "phone" in response.data


def test_patch_profile_does_not_leak_other_users(authed_client_factory, user_factory):
    """Patching my profile must never read or touch another user's row."""
    other = user_factory(email="other@example.test")
    other.profile.display_name = "Other Name"
    other.profile.save()
    client, me = authed_client_factory()
    response = client.patch(
        reverse("my-profile"),
        {"display_name": "My New Name"},
        format="json",
    )
    assert response.status_code == 200
    other.profile.refresh_from_db()
    assert other.profile.display_name == "Other Name"
    me.profile.refresh_from_db()
    assert me.profile.display_name == "My New Name"
