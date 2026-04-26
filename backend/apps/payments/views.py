"""Payments views: PaymentIntent creation + Stripe webhook receiver."""

from __future__ import annotations

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking

from .services import (
    create_checkout_session,
    create_payment_intent,
    handle_webhook_event,
    verify_checkout_session,
)


class StripeConfigView(APIView):
    """Returns the publishable key so the browser knows whether to even
    attempt loading Stripe Elements. Anonymous OK — keys are public."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        configured = (
            settings.STRIPE_PUBLISHABLE_KEY.startswith("pk_")
            and "replace_me" not in settings.STRIPE_PUBLISHABLE_KEY
        )
        return Response(
            {
                "configured": configured,
                "publishable_key": settings.STRIPE_PUBLISHABLE_KEY if configured else "",
            }
        )


class PaymentIntentView(APIView):
    """POST {booking: <id>} → {client_secret, amount_cents, ...}.

    Requires the renter to be authenticated and to own the booking.
    Booking must be `accepted` and `payment_method=stripe`.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get("booking")
        if not booking_id:
            return Response({"booking": ["Required."]}, status=400)
        booking = get_object_or_404(Booking, pk=booking_id)
        if booking.renter_id != request.user.id:
            return Response({"detail": "Not your booking."}, status=403)
        payment = create_payment_intent(booking)
        return Response(
            {
                "client_secret": payment.client_secret,
                "amount_cents": payment.amount_cents,
                "currency": payment.currency,
                "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            }
        )


class CheckoutSessionView(APIView):
    """POST {booking, return_to} → {url} of a hosted Stripe Checkout
    session. Frontend redirects window.location to that URL; Stripe
    sends the renter back to ?stripe_session=cs_... when done."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get("booking")
        return_to = request.data.get("return_to") or "/dashboard/bookings"
        if not booking_id:
            return Response({"booking": ["Required."]}, status=400)
        booking = get_object_or_404(Booking, pk=booking_id)
        if booking.renter_id != request.user.id:
            return Response({"detail": "Not your booking."}, status=403)

        # Build absolute URLs Stripe can redirect back to. The Host
        # header reflects whatever the browser called (usually
        # localhost:3000 in dev), so this works in any environment.
        host = request.headers.get("Origin") or request.headers.get("Referer", "").rsplit("/", 1)[0]
        if not host:
            host = "http://localhost:3000"
        success_url = f"{host}{return_to}"
        cancel_url = success_url

        url = create_checkout_session(booking, success_url, cancel_url)
        return Response({"url": url})


class VerifySessionView(APIView):
    """POST {booking, session_id} → returns the (possibly updated)
    booking. Called by the renter after Stripe redirects them back."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        booking_id = request.data.get("booking")
        session_id = request.data.get("session_id")
        if not booking_id or not session_id:
            return Response({"detail": "booking and session_id required."}, status=400)
        booking = get_object_or_404(Booking, pk=booking_id)
        if booking.renter_id != request.user.id:
            return Response({"detail": "Not your booking."}, status=403)
        booking = verify_checkout_session(booking, session_id)
        return Response({"booking_id": booking.id, "state": booking.state})


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    """Stripe webhook receiver.

    CSRF exempt because Stripe POSTs from outside our origin. Signature
    verification on the raw body is the integrity guarantee — see
    apps.payments.services.handle_webhook_event.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        event_id = handle_webhook_event(request.body, sig)
        return Response({"received": True, "event_id": event_id}, status=200)
