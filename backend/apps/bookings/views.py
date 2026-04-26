"""Booking views."""

from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Listing

from .models import Booking, BookingState, PaymentMethod
from .serializers import BookingDetailSerializer, BookingSerializer
from .services import calculate_booking_price, create_booking, transition


def _parse_iso_dt(value: str) -> datetime:
    # Python 3.11+ accepts trailing 'Z' too.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class BookingListCreate(APIView):
    """GET my bookings (renter / owner / all). POST creates one."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = request.query_params.get("role", "all")
        qs = Booking.objects.select_related("listing", "renter", "listing__owner").prefetch_related(
            "listing__photos"
        )
        if role == "renter":
            qs = qs.filter(renter=request.user)
        elif role == "owner":
            qs = qs.filter(listing__owner=request.user)
        else:
            qs = qs.filter(Q(renter=request.user) | Q(listing__owner=request.user))
        return Response(BookingSerializer(qs, many=True).data)

    def post(self, request):
        listing_id = request.data.get("listing")
        start = request.data.get("start_at")
        end = request.data.get("end_at")
        payment_method = request.data.get("payment_method", PaymentMethod.CASH.value)
        note = request.data.get("note", "")
        if not (listing_id and start and end):
            return Response(
                {"detail": "listing, start_at, end_at are required."},
                status=400,
            )
        listing = get_object_or_404(Listing, pk=listing_id)
        try:
            start_at = _parse_iso_dt(start)
            end_at = _parse_iso_dt(end)
        except ValueError:
            return Response(
                {"detail": "Datetimes must be ISO 8601 with offset."},
                status=400,
            )

        booking = create_booking(
            listing,
            request.user,
            start_at,
            end_at,
            payment_method=payment_method,
            note=note,
        )
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetail(APIView):
    """GET full booking with timeline. PATCH performs an FSM transition."""

    permission_classes = [permissions.IsAuthenticated]

    def _booking_for_user(self, request, id):
        booking = get_object_or_404(
            Booking.objects.select_related("listing", "renter", "listing__owner").prefetch_related(
                "transitions__actor", "listing__photos"
            ),
            pk=id,
        )
        if request.user.id not in (booking.renter_id, booking.listing.owner_id):
            return None
        return booking

    def get(self, request, id):
        booking = self._booking_for_user(request, id)
        if booking is None:
            return Response({"detail": "Not found."}, status=404)
        return Response(BookingDetailSerializer(booking).data)

    def patch(self, request, id):
        booking = self._booking_for_user(request, id)
        if booking is None:
            return Response({"detail": "Not found."}, status=404)
        to_state = request.data.get("state")
        reason = request.data.get("reason", "")
        if not to_state:
            return Response({"state": ["Provide a new state."]}, status=400)
        transition(booking, to_state, actor=request.user, reason=reason)
        return Response(BookingDetailSerializer(booking).data)


class OwnerAnalyticsView(APIView):
    """Aggregate stats for everything the signed-in owner has rented out.
    Backs the /dashboard/analytics page."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        listings_qs = Listing.objects.filter(owner=user)
        listings_total = listings_qs.count()
        listings_active = listings_qs.filter(is_active=True).count()

        bookings_qs = Booking.objects.filter(listing__owner=user)
        bookings_total = bookings_qs.count()

        # Earned revenue: completed bookings only ("realised").
        # Pipeline revenue: anything past payment but not yet completed.
        earned = bookings_qs.filter(state=BookingState.COMPLETED.value).aggregate(
            s=Sum("total_amount")
        )["s"] or Decimal("0")
        pipeline_states = [
            BookingState.PAID.value,
            BookingState.PICKED_UP.value,
            BookingState.RETURNED.value,
        ]
        pipeline = bookings_qs.filter(state__in=pipeline_states).aggregate(s=Sum("total_amount"))[
            "s"
        ] or Decimal("0")

        # State distribution → ordered list so the frontend can render
        # the bar chart deterministically without sorting.
        state_order = [
            BookingState.REQUESTED.value,
            BookingState.ACCEPTED.value,
            BookingState.PAID.value,
            BookingState.PICKED_UP.value,
            BookingState.RETURNED.value,
            BookingState.COMPLETED.value,
            BookingState.REJECTED.value,
            BookingState.CANCELLED.value,
            BookingState.DISPUTED.value,
        ]
        state_counts = dict(bookings_qs.values_list("state").annotate(c=Count("id")))
        state_breakdown = [{"state": s, "count": state_counts.get(s, 0)} for s in state_order]

        # Conversion: of every booking that left REQUESTED (i.e. owner
        # acted on it), what fraction did they accept rather than reject?
        decided = bookings_qs.exclude(state=BookingState.REQUESTED.value).count()
        accepted_or_better = bookings_qs.exclude(
            state__in=[
                BookingState.REQUESTED.value,
                BookingState.REJECTED.value,
                BookingState.CANCELLED.value,
            ]
        ).count()
        acceptance_rate = round(accepted_or_better / decided * 100) if decided else 0

        # 30-day window for "recent" totals.
        since = timezone.now() - timedelta(days=30)
        last_30d = bookings_qs.filter(created_at__gte=since)
        last_30d_count = last_30d.count()
        last_30d_revenue = last_30d.filter(state=BookingState.COMPLETED.value).aggregate(
            s=Sum("total_amount")
        )["s"] or Decimal("0")

        # Top 5 listings by booking count + lifetime revenue.
        top_listings_qs = listings_qs.annotate(
            booking_count=Count("bookings"),
            revenue=Sum(
                "bookings__total_amount",
                filter=Q(bookings__state=BookingState.COMPLETED.value),
            ),
        ).order_by("-booking_count", "-revenue")[:5]
        top_listings = [
            {
                "id": listing.id,
                "title": listing.title,
                "category": listing.category,
                "district": listing.district,
                "is_active": listing.is_active,
                "booking_count": listing.booking_count or 0,
                "revenue": str(listing.revenue or Decimal("0")),
            }
            for listing in top_listings_qs
        ]

        # Last 5 bookings across the owner's listings.
        recent_qs = bookings_qs.select_related("listing", "renter").order_by("-created_at")[:5]
        recent = [
            {
                "id": b.id,
                "listing_id": b.listing_id,
                "listing_title": b.listing.title,
                "renter_display_name": (
                    getattr(getattr(b.renter, "profile", None), "display_name", "")
                    or b.renter.email
                ),
                "state": b.state,
                "payment_method": b.payment_method,
                "total_amount": str(b.total_amount),
                "start_at": b.start_at.isoformat(),
                "created_at": b.created_at.isoformat(),
            }
            for b in recent_qs
        ]

        return Response(
            {
                "listings_total": listings_total,
                "listings_active": listings_active,
                "bookings_total": bookings_total,
                "earned_revenue": str(earned),
                "pipeline_revenue": str(pipeline),
                "acceptance_rate": acceptance_rate,
                "last_30d_count": last_30d_count,
                "last_30d_revenue": str(last_30d_revenue),
                "state_breakdown": state_breakdown,
                "top_listings": top_listings,
                "recent_bookings": recent,
            }
        )


class BookingPriceQuote(APIView):
    """POST {listing, start_at, end_at} → price preview without saving."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        listing_id = request.data.get("listing")
        start = request.data.get("start_at")
        end = request.data.get("end_at")
        if not (listing_id and start and end):
            return Response({"detail": "listing, start_at, end_at required."}, status=400)
        listing = get_object_or_404(Listing, pk=listing_id, is_active=True)
        try:
            start_at = _parse_iso_dt(start)
            end_at = _parse_iso_dt(end)
        except ValueError:
            return Response({"detail": "Datetimes must be ISO 8601 with offset."}, status=400)
        unit, unit_price, quantity, total = calculate_booking_price(listing, start_at, end_at)
        return Response(
            {
                "unit": unit,
                "unit_price": str(unit_price),
                "quantity": quantity,
                "total_amount": str(total),
            }
        )
