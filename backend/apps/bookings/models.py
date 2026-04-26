"""Booking model: 9-state FSM with timezone-aware windows.

States (BOOK-05):

    requested ─┬──► accepted ─┬──► picked_up ──► returned ──► completed
               │              │
               │              ├──► cancelled
               │              └──► paid ──────► picked_up ─...
               ├──► rejected
               └──► cancelled

    Any state ──► disputed (admin lever)

Pricing snapshot (BOOK-02): unit_price, unit, quantity, total_amount are
locked at creation. Owner editing tier prices later does not change the
booked total.

Double-booking guard (BOOK-04): Postgres ExclusionConstraint over
TsTzRange(start_at, end_at) filtered to states that hold the listing.
Requires btree_gist extension (loaded in scripts/init_extensions.sql).

Audit trail (BOOK-06): every state change writes a BookingStateTransition
row inside the same transaction.atomic() block as the Booking save.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeBoundary, RangeOperators
from django.db import models
from django.db.models import F, Func, Q

from apps.catalog.models import Listing


class BookingState(models.TextChoices):
    REQUESTED = "requested", "Requested"
    ACCEPTED = "accepted", "Accepted"
    PAID = "paid", "Paid"
    PICKED_UP = "picked_up", "Picked up"
    RETURNED = "returned", "Returned"
    COMPLETED = "completed", "Completed"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    DISPUTED = "disputed", "Disputed"


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash on pickup"
    STRIPE = "stripe", "Stripe"


class PricingUnit(models.TextChoices):
    HOUR = "hour", "Hour"
    DAY = "day", "Day"
    MONTH = "month", "Month"


# States that occupy the listing for the booked window.
ACTIVE_STATES = [
    BookingState.REQUESTED,
    BookingState.ACCEPTED,
    BookingState.PAID,
    BookingState.PICKED_UP,
]


class TsTzRange(Func):
    """Postgres TSTZRANGE constructor for ExclusionConstraint."""

    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class Booking(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bookings")
    renter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    state = models.CharField(
        max_length=20,
        choices=BookingState.choices,
        default=BookingState.REQUESTED,
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=10, choices=PricingUnit.choices)
    quantity = models.PositiveIntegerField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)

    note = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            ExclusionConstraint(
                name="booking_no_overlap",
                expressions=[
                    ("listing", RangeOperators.EQUAL),
                    (
                        TsTzRange(
                            F("start_at"),
                            F("end_at"),
                            RangeBoundary(inclusive_lower=True, inclusive_upper=False),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(state__in=[s.value for s in ACTIVE_STATES]),
            ),
        ]

    def __str__(self):
        return f"Booking #{self.pk} ({self.state})"


class BookingStateTransition(models.Model):
    """Append-only audit row for every state change."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.CharField(max_length=20, choices=BookingState.choices, blank=True)
    to_state = models.CharField(max_length=20, choices=BookingState.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="booking_actions",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.booking_id}: {self.from_state or '∅'} → {self.to_state}"
