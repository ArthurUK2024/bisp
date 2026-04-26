"""Bookings admin (ADMN-02 / ADMN-03)."""

from django.contrib import admin

from .models import Booking, BookingStateTransition


class BookingStateTransitionInline(admin.TabularInline):
    model = BookingStateTransition
    extra = 0
    fields = ("from_state", "to_state", "actor", "reason", "created_at")
    readonly_fields = ("from_state", "to_state", "actor", "reason", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "listing",
        "renter",
        "state",
        "payment_method",
        "start_at",
        "end_at",
        "total_amount",
        "created_at",
    )
    list_filter = ("state", "payment_method", "unit", "created_at")
    search_fields = (
        "listing__title",
        "renter__email",
        "listing__owner__email",
    )
    readonly_fields = (
        "unit",
        "unit_price",
        "quantity",
        "total_amount",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("listing", "renter")
    inlines = [BookingStateTransitionInline]


@admin.register(BookingStateTransition)
class BookingStateTransitionAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "from_state", "to_state", "actor", "created_at")
    list_filter = ("to_state", "from_state")
    search_fields = ("booking__id", "actor__email")
    raw_id_fields = ("booking", "actor")
    readonly_fields = (
        "booking",
        "from_state",
        "to_state",
        "actor",
        "reason",
        "created_at",
    )
