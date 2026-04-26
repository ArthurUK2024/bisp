"""Payment + StripeEvent models (Phase 6).

Payment is a satellite on Booking that records the Stripe PaymentIntent
funding it. One open Payment per Booking at a time.

StripeEvent is the idempotency table — every webhook event Stripe
delivers is stored keyed by Stripe's `event.id`. Replay safety: if
Stripe re-delivers (network blips), the unique constraint on event_id
fails the insert and we short-circuit instead of double-applying the
state change.
"""

from __future__ import annotations

from django.db import models

from apps.bookings.models import Booking


class Payment(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    stripe_intent_id = models.CharField(max_length=255, unique=True)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="usd")
    status = models.CharField(max_length=32, default="created")
    client_secret = models.CharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["booking", "status"]),
        ]

    def __str__(self):
        return f"Payment {self.stripe_intent_id} ({self.status})"


class StripeEvent(models.Model):
    """Idempotency record."""

    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=128)
    received_at = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"
