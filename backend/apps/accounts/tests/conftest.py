"""Shared pytest fixtures for the accounts test suite.

Phase 2 test files import ``api_client`` / ``user_factory`` /
``authed_client_factory`` from here. Wave 1 (02-02) and Wave 2 (02-03) rely
on these fixtures, so the conftest ships in Wave 0 and no later test file
lands without a running feedback loop.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def authed_client_factory(db):
    def _make(user=None):
        user = user or UserFactory()
        access = str(RefreshToken.for_user(user).access_token)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client, user

    return _make
