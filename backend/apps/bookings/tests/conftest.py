"""Shared fixtures for the bookings test suite.

Mirrors apps/accounts/tests/conftest.py so booking tests can call
``user_factory()`` directly without reimporting the factory module
in every file.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.factories import UserFactory
from apps.catalog.models import Listing


@pytest.fixture
def user_factory():
    return UserFactory


@pytest.fixture
def listing_factory(db):
    """Build a listing with the given pricing tiers. Defaults: day-only."""

    def _make(
        owner=None,
        title="Test listing",
        category="tools",
        district="chilonzor",
        price_hour=None,
        price_day=Decimal("50000"),
        price_month=None,
        is_active=True,
    ):
        owner = owner or UserFactory()
        return Listing.objects.create(
            owner=owner,
            title=title,
            description="A test listing.",
            category=category,
            district=district,
            price_hour=price_hour,
            price_day=price_day,
            price_month=price_month,
            is_active=is_active,
        )

    return _make


@pytest.fixture
def now():
    """A stable 'now' used across tests; aligned to the next hour."""
    return timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
