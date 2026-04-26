"""Double-booking prevention via Postgres ExclusionConstraint (BOOK-04).

The constraint is over TsTzRange(start_at, end_at) filtered to active
states (requested, accepted, paid, picked_up). Inactive states
(rejected, cancelled, completed, returned, disputed) do not block.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from apps.bookings.models import BookingState
from apps.bookings.services import create_booking, transition

pytestmark = pytest.mark.django_db


def test_overlap_blocked_for_active_states(listing_factory, user_factory, now):
    owner = user_factory()
    renter1 = user_factory()
    renter2 = user_factory()
    listing = listing_factory(owner=owner)

    create_booking(
        listing,
        renter1,
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
    )

    with pytest.raises(Exception) as exc:
        # Window fully nested inside the existing booking.
        create_booking(
            listing,
            renter2,
            start_at=now + timedelta(days=3),
            end_at=now + timedelta(days=3, hours=12),
        )
    assert "overlap" in str(exc.value).lower()


def test_overlap_at_partial_edge_blocked(listing_factory, user_factory, now):
    owner = user_factory()
    listing = listing_factory(owner=owner)

    create_booking(
        listing,
        user_factory(),
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
    )

    with pytest.raises(Exception):  # noqa: B017 — Postgres exclusion constraint or DRF ValidationError, both acceptable
        # Starts before the existing one ends.
        create_booking(
            listing,
            user_factory(),
            start_at=now + timedelta(days=3),
            end_at=now + timedelta(days=5),
        )


def test_back_to_back_bookings_allowed(listing_factory, user_factory, now):
    """[start, end) is half-open; A.end == B.start does NOT overlap."""
    owner = user_factory()
    listing = listing_factory(owner=owner)

    create_booking(
        listing,
        user_factory(),
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
    )
    # Adjacent window starting exactly when the previous ended.
    create_booking(
        listing,
        user_factory(),
        start_at=now + timedelta(days=4),
        end_at=now + timedelta(days=6),
    )


def test_cancelled_booking_does_not_block(listing_factory, user_factory, now):
    owner = user_factory()
    renter1 = user_factory()
    renter2 = user_factory()
    listing = listing_factory(owner=owner)

    first = create_booking(
        listing,
        renter1,
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
    )
    transition(first, BookingState.CANCELLED.value, actor=renter1)

    # Same window now succeeds because the cancelled booking is in an
    # inactive state and dropped out of the ExclusionConstraint scope.
    create_booking(
        listing,
        renter2,
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
    )


def test_different_listings_do_not_collide(listing_factory, user_factory, now):
    a = listing_factory(title="Listing alpha")
    b = listing_factory(title="Listing bravo")
    create_booking(
        a,
        user_factory(),
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
    )
    # Same window on a different listing is fine.
    create_booking(
        b,
        user_factory(),
        start_at=now + timedelta(days=2),
        end_at=now + timedelta(days=4),
    )
