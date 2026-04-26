"""Payments admin (ADMN-04)."""

from django.contrib import admin

from .models import Payment, StripeEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "stripe_intent_id", "amount_cents", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("stripe_intent_id", "booking__id")
    raw_id_fields = ("booking",)
    readonly_fields = ("stripe_intent_id", "client_secret", "created_at", "updated_at")


@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "event_type", "received_at")
    list_filter = ("event_type",)
    search_fields = ("event_id",)
    readonly_fields = ("event_id", "event_type", "received_at", "payload")
