"""FSM transition gating + audit trail (BOOK-05, BOOK-06)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from apps.bookings.models import (
    BookingState,
)
from apps.bookings.services import create_booking, transition

pytestmark = pytest.mark.django_db


def _make(listing_factory, user_factory, now):
    owner = user_factory()
    renter = user_factory()
    listing = listing_factory(owner=owner)
    booking = create_booking(
        listing,
        renter,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=2),
    )
    return booking, owner, renter


def test_create_writes_initial_audit_row(listing_factory, user_factory, now):
    booking, _, renter = _make(listing_factory, user_factory, now)
    rows = list(booking.transitions.all())
    assert len(rows) == 1
    assert rows[0].from_state == ""
    assert rows[0].to_state == BookingState.REQUESTED.value
    assert rows[0].actor_id == renter.id


def test_owner_can_accept_then_pickup_then_return_then_complete(listing_factory, user_factory, now):
    booking, owner, _ = _make(listing_factory, user_factory, now)
    transition(booking, BookingState.ACCEPTED.value, actor=owner)
    transition(booking, BookingState.PICKED_UP.value, actor=owner)
    transition(booking, BookingState.RETURNED.value, actor=owner)
    transition(booking, BookingState.COMPLETED.value, actor=owner)
    assert booking.state == BookingState.COMPLETED.value
    assert booking.transitions.count() == 5  # initial + 4 owner steps


def test_renter_can_cancel_only_in_requested_or_accepted(listing_factory, user_factory, now):
    booking, owner, renter = _make(listing_factory, user_factory, now)
    transition(booking, BookingState.CANCELLED.value, actor=renter)
    assert booking.state == BookingState.CANCELLED.value


def test_renter_cannot_pickup(listing_factory, user_factory, now):
    booking, owner, renter = _make(listing_factory, user_factory, now)
    transition(booking, BookingState.ACCEPTED.value, actor=owner)
    with pytest.raises(Exception) as exc:
        transition(booking, BookingState.PICKED_UP.value, actor=renter)
    assert "Cannot move from accepted to picked_up as renter" in str(exc.value)


def test_third_party_user_cannot_act_on_booking(listing_factory, user_factory, now):
    booking, owner, _ = _make(listing_factory, user_factory, now)
    intruder = user_factory()
    with pytest.raises(Exception) as exc:
        transition(booking, BookingState.ACCEPTED.value, actor=intruder)
    assert "not part of this booking" in str(exc.value)


def test_system_can_mark_paid_only_from_accepted(listing_factory, user_factory, now):
    booking, owner, _ = _make(listing_factory, user_factory, now)
    transition(booking, BookingState.ACCEPTED.value, actor=owner)
    # actor=None resolves to "system" — Stripe webhook path.
    transition(booking, BookingState.PAID.value, actor=None, reason="stripe webhook")
    assert booking.state == BookingState.PAID.value
    last = booking.transitions.order_by("-created_at").first()
    assert last.actor is None
    assert last.reason == "stripe webhook"


def test_owner_with_staff_flag_still_acts_as_owner(listing_factory, user_factory, now):
    """Owner/renter relationship outranks staff status."""
    booking, owner, _ = _make(listing_factory, user_factory, now)
    owner.is_staff = True
    owner.save(update_fields=["is_staff"])
    transition(booking, BookingState.ACCEPTED.value, actor=owner)
    assert booking.state == BookingState.ACCEPTED.value


def test_stripe_booking_owner_cannot_pickup_before_payment(listing_factory, user_factory, now):
    """For payment_method=stripe, accepted → picked_up is blocked.
    Path is accepted → paid (via Stripe webhook) → picked_up.
    Cash bookings settle at handover so this guard does NOT apply."""
    from apps.bookings.models import PaymentMethod

    owner = user_factory()
    renter = user_factory()
    listing = listing_factory(owner=owner)
    booking = create_booking(
        listing,
        renter,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=2),
        payment_method=PaymentMethod.STRIPE.value,
    )
    transition(booking, BookingState.ACCEPTED.value, actor=owner)
    with pytest.raises(Exception) as exc:
        transition(booking, BookingState.PICKED_UP.value, actor=owner)
    assert "stripe" in str(exc.value).lower()

    # Once the system marks paid, pickup unlocks.
    transition(booking, BookingState.PAID.value, actor=None, reason="webhook")
    transition(booking, BookingState.PICKED_UP.value, actor=owner)
    assert booking.state == BookingState.PICKED_UP.value


def test_audit_trail_records_actor_and_reason(listing_factory, user_factory, now):
    booking, owner, _ = _make(listing_factory, user_factory, now)
    transition(
        booking,
        BookingState.ACCEPTED.value,
        actor=owner,
        reason="picked it up at noon",
    )
    last = booking.transitions.order_by("-created_at").first()
    assert last.from_state == BookingState.REQUESTED.value
    assert last.to_state == BookingState.ACCEPTED.value
    assert last.actor_id == owner.id
    assert last.reason == "picked it up at noon"
