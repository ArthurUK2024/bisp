"""Tests for the health endpoint — the Phase 1 smoke test.

ATOMIC_REQUESTS=True (Phase 2 setting) means every request acquires a
DB connection, so the test client needs the `db` fixture even though
the health view itself doesn't query anything.
"""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


def test_health_returns_ok(client):
    response = client.get("/api/v1/health/")
    assert response.status_code == 200


def test_health_shape(client):
    response = client.get("/api/v1/health/")
    body = response.json()
    assert set(body.keys()) == {"status", "git_sha"}
    assert body["status"] == "ok"


def test_health_reads_env(client, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc123")
    response = client.get("/api/v1/health/")
    assert response.json()["git_sha"] == "abc123"


def test_health_defaults_git_sha_when_unset(client, monkeypatch):
    monkeypatch.delenv("GIT_SHA", raising=False)
    response = client.get("/api/v1/health/")
    assert response.json()["git_sha"] == "unknown"
