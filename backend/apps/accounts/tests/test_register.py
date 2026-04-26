"""AUTH-01 — register endpoint tests."""

import pytest
from django.urls import reverse

from apps.accounts.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_register_success(api_client):
    url = reverse("register")
    response = api_client.post(
        url,
        {"email": "alice@example.test", "password": "zx7mnp45"},
        format="json",
    )
    assert response.status_code == 201
    assert set(response.data.keys()) == {"id", "email"}
    assert response.data["email"] == "alice@example.test"


@pytest.mark.parametrize(
    "bad_password,reason",
    [
        ("abcdefgh", "letters_only"),
        ("12345678", "digits_only"),
        ("abc1", "too_short"),
    ],
)
def test_register_rejects_bad_password(api_client, bad_password, reason):
    url = reverse("register")
    response = api_client.post(
        url,
        {"email": f"u-{reason}@example.test", "password": bad_password},
        format="json",
    )
    assert response.status_code == 400
    assert "password" in response.data


def test_register_rejects_duplicate_email_case_insensitive(api_client):
    UserFactory(email="Alice@Example.test")
    url = reverse("register")
    response = api_client.post(
        url,
        {"email": "alice@example.test", "password": "zx7mnp45"},
        format="json",
    )
    assert response.status_code == 400
    assert "email" in response.data


def test_register_response_shape(api_client):
    url = reverse("register")
    response = api_client.post(
        url,
        {"email": "bob@example.test", "password": "zx7mnp45"},
        format="json",
    )
    assert "password" not in response.data
    assert "access" not in response.data
    assert "refresh" not in response.data


def test_register_missing_fields_returns_400(api_client):
    url = reverse("register")
    response = api_client.post(url, {}, format="json")
    assert response.status_code == 400
    assert "email" in response.data
    assert "password" in response.data
