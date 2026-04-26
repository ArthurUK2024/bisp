"""Booking services: pricing, creation, FSM transitions.

The transition() function is the single legal writer of Booking.state.
A grep across views/admin/webhooks for ``booking.state =`` should find
zero matches outside this module — that invariant is what keeps the
audit trail in BookingStateTransition complete.
"""

from __future__ import annotations

import math
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone as dj_tz
from rest_framework.exceptions import ValidationError

from .models import (
    Booking,
    BookingState,
    BookingStateTransition,
    PaymentMethod,
    PricingUnit,
)

# Seconds per pricing unit, used by the pricing calculator.
_UNIT_SECONDS = {
    PricingUnit.HOUR: 60 * 60,
    PricingUnit.DAY: 24 * 60 * 60,
    PricingUnit.MONTH: 30 * 24 * 60 * 60,
}


# -----------------------------------------------------------------------------
# Pricing calculator (BOOK-02)
# -----------------------------------------------------------------------------


def _quantize(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_booking_price(listing, start_at: datetime, end_at: datetime):
    """Pick the cheapest pricing unit for the requested window.

    Rule: try every available tier (hour/day/month) the listing has set,
    round the duration UP to whole units, multiply by the tier's unit
    price, and pick the minimum total. Returns (unit, unit_price,
    quantity, total_amount). Raises ValidationError if the listing has
    no pricing tiers at all.
    """
    if end_at <= start_at:
        raise ValidationError({"end_at": ["End time must be after start time."]})

    duration_seconds = (end_at - start_at).total_seconds()
    candidates: list[tuple[Decimal, str, Decimal, int]] = []

    tier_prices = {
        PricingUnit.HOUR: listing.price_hour,
        PricingUnit.DAY: listing.price_day,
        PricingUnit.MONTH: listing.price_month,
    }

    for unit, price in tier_prices.items():
        if price is None:
            continue
        unit_seconds = _UNIT_SECONDS[unit]
        quantity = max(1, math.ceil(duration_seconds / unit_seconds))
        total = _quantize(Decimal(quantity) * Decimal(price))
        candidates.append((total, unit.value, Decimal(price), quantity))

    if not candidates:
        raise ValidationError({"listing": ["This listing has no pricing tiers set."]})

    candidates.sort(key=lambda c: c[0])
    total, unit_value, unit_price, quantity = candidates[0]
    return unit_value, unit_price, quantity, total


# -----------------------------------------------------------------------------
# Booking creation (BOOK-01, BOOK-04)
# -----------------------------------------------------------------------------


def create_booking(
    listing,
    renter,
    start_at: datetime,
    end_at: datetime,
    payment_method: str = PaymentMethod.CASH.value,
    note: str = "",
) -> Booking:
    """Validate, price, and persist a booking. Atomic with audit row."""
    if not listing.is_active:
        raise ValidationError({"listing": ["This listing is no longer available."]})
    if renter.id == listing.owner_id:
        raise ValidationError({"listing": ["You cannot book your own listing."]})

    if start_at.tzinfo is None or end_at.tzinfo is None:
        raise ValidationError({"start_at": ["Datetimes must include an explicit timezone offset."]})

    now = dj_tz.now()
    if start_at < now:
        raise ValidationError({"start_at": ["Start time cannot be in the past."]})

    unit, unit_price, quantity, total = calculate_booking_price(listing, start_at, end_at)

    booking = Booking(
        listing=listing,
        renter=renter,
        start_at=start_at,
        end_at=end_at,
        state=BookingState.REQUESTED.value,
        payment_method=payment_method,
        unit=unit,
        unit_price=unit_price,
        quantity=quantity,
        total_amount=total,
        note=note,
    )

    try:
        with transaction.atomic():
            booking.save()
            BookingStateTransition.objects.create(
                booking=booking,
                from_state="",
                to_state=BookingState.REQUESTED.value,
                actor=renter,
                reason="created",
            )
    except IntegrityError as exc:
        # ExclusionConstraint blocked an overlapping booking for this listing.
        raise ValidationError(
            {"start_at": ["Those dates overlap with an existing booking."]}
        ) from exc

    return booking


# -----------------------------------------------------------------------------
# FSM transition gate (BOOK-05, BOOK-06)
# -----------------------------------------------------------------------------

# Allowed transitions per actor role.
# "owner" is the listing owner, "renter" is the booking renter,
# "system" is non-user actors like the Stripe webhook.
_TRANSITIONS: dict[str, dict[str, list[str]]] = {
    "owner": {
        BookingState.REQUESTED.value: [
            BookingState.ACCEPTED.value,
            BookingState.REJECTED.value,
        ],
        BookingState.ACCEPTED.value: [
            BookingState.PICKED_UP.value,
            BookingState.CANCELLED.value,
        ],
        BookingState.PAID.value: [
            BookingState.PICKED_UP.value,
            BookingState.CANCELLED.value,
        ],
        BookingState.PICKED_UP.value: [BookingState.RETURNED.value],
        BookingState.RETURNED.value: [BookingState.COMPLETED.value],
    },
    "renter": {
        BookingState.REQUESTED.value: [BookingState.CANCELLED.value],
        BookingState.ACCEPTED.value: [BookingState.CANCELLED.value],
    },
    "system": {
        # Stripe webhook is the only writer of `paid`.
        BookingState.ACCEPTED.value: [BookingState.PAID.value],
    },
    "admin": {
        # Staff can put anything into disputed for triage.
        BookingState.REQUESTED.value: [BookingState.DISPUTED.value],
        BookingState.ACCEPTED.value: [BookingState.DISPUTED.value],
        BookingState.PAID.value: [BookingState.DISPUTED.value],
        BookingState.PICKED_UP.value: [BookingState.DISPUTED.value],
        BookingState.RETURNED.value: [BookingState.DISPUTED.value],
    },
}


def _resolve_role(booking: Booking, actor) -> str:
    if actor is None:
        return "system"
    # Owner / renter relationships outrank staff status, so a staff
    # member acting on their own booking still goes through the normal
    # owner/renter gates rather than the broader admin lever.
    if actor.id == booking.listing.owner_id:
        return "owner"
    if actor.id == booking.renter_id:
        return "renter"
    if getattr(actor, "is_staff", False):
        return "admin"
    raise ValidationError({"detail": ["You are not part of this booking."]})


def transition(
    booking: Booking,
    to_state: str,
    actor=None,
    reason: str = "",
) -> Booking:
    """Single legal writer of Booking.state. Atomic with audit row."""
    role = _resolve_role(booking, actor)
    allowed = _TRANSITIONS.get(role, {}).get(booking.state, [])
    if to_state not in allowed:
        raise ValidationError(
            {"state": [f"Cannot move from {booking.state} to {to_state} as {role}."]}
        )

    # Stripe bookings must clear payment before the owner can mark
    # pickup. Cash-on-pickup is the alternate path: money changes hands
    # at handover, so accepted → picked_up is correct for that case.
    if (
        to_state == BookingState.PICKED_UP.value
        and booking.state == BookingState.ACCEPTED.value
        and booking.payment_method == PaymentMethod.STRIPE.value
    ):
        raise ValidationError(
            {
                "state": [
                    "This booking is set to Stripe — wait for the renter to "
                    "pay before marking pickup."
                ]
            }
        )

    from_state = booking.state
    with transaction.atomic():
        booking.state = to_state
        booking.save(update_fields=["state", "updated_at"])
        BookingStateTransition.objects.create(
            booking=booking,
            from_state=from_state,
            to_state=to_state,
            actor=actor,
            reason=reason,
        )
    return booking
