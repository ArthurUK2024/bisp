"""AUTH-06 supporting backend checks — /me/ permissions and shape."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_me_requires_auth(api_client):
    response = api_client.get(reverse("me"))
    assert response.status_code == 401


def test_me_returns_user_shape_with_token(authed_client_factory):
    client, user = authed_client_factory()
    response = client.get(reverse("me"))
    assert response.status_code == 200
    assert set(response.data.keys()) == {"id", "email", "date_joined", "is_staff"}
    assert response.data["email"] == user.email
    assert response.data["is_staff"] is False


def test_me_does_not_expose_password_hash(authed_client_factory):
    client, user = authed_client_factory()
    response = client.get(reverse("me"))
    raw = str(response.data)
    assert "pbkdf2" not in raw
    assert user.password not in raw


def test_me_with_invalid_token_returns_401(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not.a.real.jwt")
    response = api_client.get(reverse("me"))
    assert response.status_code == 401
