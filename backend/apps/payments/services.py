"""Stripe service layer.

create_payment_intent: builds a Stripe PaymentIntent for a booking,
stores the Payment row, returns client_secret for the frontend
Payment Element.

handle_webhook_event: verifies signature on the raw body, dedupes
via StripeEvent.event_id (unique constraint), and routes the verified
event into booking_service.transition. payment_intent.succeeded is
the ONLY caller that writes the `paid` state.
"""

from __future__ import annotations

from decimal import Decimal

import stripe
from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException, ValidationError

from apps.bookings.models import Booking, BookingState, PaymentMethod
from apps.bookings.services import transition

from .models import Payment, StripeEvent


class StripeNotConfigured(APIException):
    status_code = 503
    default_detail = "Stripe is not configured for this environment."
    default_code = "stripe_not_configured"


# Stripe test mode does not support UZS, so amounts are sent in USD with
# a documented conversion rate. The report's Methodology chapter frames
# this as the "production swap to Click/Payme" decision.
USD_PER_UZS = Decimal("0.000079")


def _ensure_configured() -> None:
    if not settings.STRIPE_SECRET_KEY or "replace_me" in settings.STRIPE_SECRET_KEY:
        raise StripeNotConfigured()
    stripe.api_key = settings.STRIPE_SECRET_KEY


def amount_to_cents(uzs_total: Decimal) -> int:
    """Convert a UZS booking total into USD cents Stripe can charge."""
    usd = (Decimal(uzs_total) * USD_PER_UZS).quantize(Decimal("0.01"))
    return max(50, int(usd * 100))  # Stripe minimum is $0.50


def _guard_stripe_booking(booking: Booking) -> None:
    if booking.payment_method != PaymentMethod.STRIPE.value:
        raise ValidationError({"payment_method": ["This booking is set to cash on pickup."]})
    if booking.state != BookingState.ACCEPTED.value:
        raise ValidationError(
            {"state": ["Stripe payment is only available once the owner accepts the booking."]}
        )


def create_payment_intent(booking: Booking) -> Payment:
    """Embedded Payment Element flow (kept for backward compatibility)."""
    _ensure_configured()
    _guard_stripe_booking(booking)

    amount = amount_to_cents(booking.total_amount)
    intent = stripe.PaymentIntent.create(
        amount=amount,
        currency="usd",
        metadata={"booking_id": str(booking.id), "renter_id": str(booking.renter_id)},
        automatic_payment_methods={"enabled": True},
    )

    payment, _ = Payment.objects.update_or_create(
        booking=booking,
        stripe_intent_id=intent.id,
        defaults={
            "amount_cents": amount,
            "currency": "usd",
            "status": intent.status,
            "client_secret": intent.client_secret,
        },
    )
    return payment


def create_checkout_session(booking: Booking, success_url: str, cancel_url: str) -> str:
    """Hosted Stripe Checkout — return the URL the renter should be
    redirected to. Stripe sends the user back to success_url after
    payment with ?session_id=cs_... in the query string. We then call
    verify_checkout_session() to flip the booking to paid; the webhook
    is a backup path, not a hard dependency.
    """
    _ensure_configured()
    _guard_stripe_booking(booking)

    amount = amount_to_cents(booking.total_amount)
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": booking.listing.title,
                        "description": (
                            f"Booking #{booking.id} — {booking.quantity} {booking.unit}(s)"
                        ),
                    },
                    "unit_amount": amount,
                },
                "quantity": 1,
            }
        ],
        success_url=f"{success_url}?stripe_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{cancel_url}?stripe_cancelled=1",
        metadata={
            "booking_id": str(booking.id),
            "renter_id": str(booking.renter_id),
        },
    )

    Payment.objects.update_or_create(
        booking=booking,
        stripe_intent_id=session.id,
        defaults={
            "amount_cents": amount,
            "currency": "usd",
            "status": "checkout_pending",
            "client_secret": session.url or "",
        },
    )
    return session.url


def verify_checkout_session(booking: Booking, session_id: str) -> Booking:
    """Called when Stripe redirects the renter back. Confirms the
    session is paid against Stripe's API, then transitions the booking.
    Idempotent: a second call after the booking is already in `paid`
    is a no-op.
    """
    _ensure_configured()

    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.InvalidRequestError as exc:
        raise ValidationError({"stripe_session": ["Unknown session."]}) from exc

    booking_meta = (session.metadata or {}).get("booking_id")
    if str(booking.id) != str(booking_meta):
        raise ValidationError({"stripe_session": ["Session does not match this booking."]})

    if session.payment_status != "paid":
        raise ValidationError(
            {"stripe_session": [f"Payment not completed (status: {session.payment_status})."]}
        )

    payment = Payment.objects.filter(booking=booking, stripe_intent_id=session.id).first()
    if payment:
        payment.status = "succeeded"
        payment.save(update_fields=["status", "updated_at"])

    if booking.state == BookingState.ACCEPTED.value:
        transition(
            booking,
            BookingState.PAID.value,
            actor=None,
            reason=f"stripe checkout: {session.id}",
        )
    return booking


def handle_webhook_event(payload_bytes: bytes, sig_header: str) -> str:
    """Verify, dedupe, route. Returns event id."""
    _ensure_configured()
    try:
        event = stripe.Webhook.construct_event(
            payload_bytes,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise ValidationError({"signature": ["Invalid Stripe signature."]}) from exc

    try:
        with transaction.atomic():
            StripeEvent.objects.create(
                event_id=event["id"],
                event_type=event["type"],
                payload=event,
            )
    except IntegrityError:
        # Stripe re-delivered an event we already processed — short-circuit.
        return event["id"]

    if event["type"] == "payment_intent.succeeded":
        _on_intent_succeeded(event["data"]["object"])
    elif event["type"] in (
        "payment_intent.payment_failed",
        "payment_intent.canceled",
    ):
        _on_intent_failed(event["data"]["object"])

    return event["id"]


def _on_intent_succeeded(intent: dict) -> None:
    payment = (
        Payment.objects.select_related("booking").filter(stripe_intent_id=intent["id"]).first()
    )
    if not payment:
        return
    payment.status = "succeeded"
    payment.save(update_fields=["status", "updated_at"])

    booking = payment.booking
    if booking.state == BookingState.ACCEPTED.value:
        # actor=None routes through booking_service.transition's "system"
        # role — the only path allowed to write `paid`.
        transition(
            booking,
            BookingState.PAID.value,
            actor=None,
            reason=f"stripe webhook: {intent['id']}",
        )


def _on_intent_failed(intent: dict) -> None:
    payment = Payment.objects.filter(stripe_intent_id=intent["id"]).first()
    if not payment:
        return
    payment.status = intent.get("status", "failed")
    payment.save(update_fields=["status", "updated_at"])
