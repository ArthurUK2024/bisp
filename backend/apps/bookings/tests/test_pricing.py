"""Pricing calculator coverage (BOOK-02).

Rule: pick the cheapest unit (hour / day / month) for the requested
window, rounding the duration UP to whole units. Decimal math.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.bookings.services import calculate_booking_price

pytestmark = pytest.mark.django_db


# (label, hours, hour_price, day_price, month_price, expected_unit, expected_qty, expected_total)
WINDOWS = [
    ("1h on hour-only", 1, 5000, None, None, "hour", 1, "5000.00"),
    ("23h day cheaper than hours", 23, 5000, 50000, None, "day", 1, "50000.00"),
    ("24h is exactly 1 day", 24, 5000, 50000, None, "day", 1, "50000.00"),
    ("25h rounds up to 2 days", 25, 5000, 50000, None, "day", 2, "100000.00"),
    ("7d on day-only", 7 * 24, None, 50000, None, "day", 7, "350000.00"),
    ("30d day vs month — month wins", 30 * 24, None, 50000, 1_000_000, "month", 1, "1000000.00"),
    # 31d × 50k/day = 1.55M < 2 × 1M/month = 2M → day still wins.
    (
        "31d day still cheaper than 2 months",
        31 * 24,
        None,
        50000,
        1_000_000,
        "day",
        31,
        "1550000.00",
    ),
    # 60d × 50k/day = 3M > 2 × 1M/month = 2M → month wins.
    ("60d month wins over 60 days", 60 * 24, None, 50000, 1_000_000, "month", 2, "2000000.00"),
    ("single tier hour-only over 5h", 5, 5000, None, None, "hour", 5, "25000.00"),
]


@pytest.mark.parametrize(
    "label,hours,price_hour,price_day,price_month,unit,quantity,total",
    WINDOWS,
)
def test_pricing_window(
    listing_factory,
    now,
    label,
    hours,
    price_hour,
    price_day,
    price_month,
    unit,
    quantity,
    total,
):
    listing = listing_factory(
        price_hour=Decimal(price_hour) if price_hour else None,
        price_day=Decimal(price_day) if price_day else None,
        price_month=Decimal(price_month) if price_month else None,
    )
    start = now
    end = now + timedelta(hours=hours)
    out_unit, out_unit_price, out_quantity, out_total = calculate_booking_price(listing, start, end)
    assert out_unit == unit, label
    assert out_quantity == quantity, label
    assert out_total == Decimal(total), label


def test_pricing_picks_cheapest_when_multiple_tiers(listing_factory, now):
    """Two-day window: day = 100k vs hour = 60k × 48h = 2.88M. Day wins."""
    listing = listing_factory(
        price_hour=Decimal("60000"),
        price_day=Decimal("100000"),
        price_month=None,
    )
    out_unit, _, out_quantity, out_total = calculate_booking_price(
        listing, now, now + timedelta(hours=48)
    )
    assert out_unit == "day"
    assert out_quantity == 2
    assert out_total == Decimal("200000.00")


def test_pricing_rejects_zero_window(listing_factory, now):
    listing = listing_factory()
    with pytest.raises(Exception) as exc:
        calculate_booking_price(listing, now, now)
    assert "End time must be after start time" in str(exc.value)


def test_pricing_rejects_listing_with_no_tiers(listing_factory, now):
    """Listing.clean() blocks the empty-tier shape at save time, so we
    construct the listing with day-only pricing then null all tiers
    in-memory before calling the calculator. Exercises the calculator's
    own guard (defence in depth)."""
    listing = listing_factory()
    listing.price_hour = None
    listing.price_day = None
    listing.price_month = None
    with pytest.raises(Exception) as exc:
        calculate_booking_price(listing, now, now + timedelta(hours=24))
    assert "no pricing tiers" in str(exc.value)
