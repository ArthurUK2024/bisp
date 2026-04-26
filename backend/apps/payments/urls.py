"""Payments URL routes."""

from django.urls import path

from .views import (
    CheckoutSessionView,
    PaymentIntentView,
    StripeConfigView,
    StripeWebhookView,
    VerifySessionView,
)

urlpatterns = [
    path("payments/config/", StripeConfigView.as_view(), name="stripe-config"),
    path("payments/intent/", PaymentIntentView.as_view(), name="payment-intent"),
    path("payments/checkout/", CheckoutSessionView.as_view(), name="checkout-session"),
    path("payments/verify/", VerifySessionView.as_view(), name="verify-session"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
