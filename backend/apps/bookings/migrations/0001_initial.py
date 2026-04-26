"""Initial booking schema with 9-state FSM, audit trail, and overlap guard.

Hand-written migration. Re-generation via makemigrations would clobber
the ExclusionConstraint expression detail (TsTzRange + RangeBoundary),
so the canonical source for the constraint shape is this file.
"""

import django.db.models.deletion
from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeBoundary, RangeOperators
from django.contrib.postgres.operations import BtreeGistExtension
from django.db import migrations, models
from django.db.models import F, Q

from apps.bookings.models import TsTzRange


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("catalog", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.CreateModel(
            name="Booking",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField()),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("accepted", "Accepted"),
                            ("paid", "Paid"),
                            ("picked_up", "Picked up"),
                            ("returned", "Returned"),
                            ("completed", "Completed"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                            ("disputed", "Disputed"),
                        ],
                        default="requested",
                        max_length=20,
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        choices=[("cash", "Cash on pickup"), ("stripe", "Stripe")],
                        default="cash",
                        max_length=10,
                    ),
                ),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "unit",
                    models.CharField(
                        choices=[("hour", "Hour"), ("day", "Day"), ("month", "Month")],
                        max_length=10,
                    ),
                ),
                ("quantity", models.PositiveIntegerField()),
                ("total_amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("note", models.TextField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "listing",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to="catalog.listing",
                    ),
                ),
                (
                    "renter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bookings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BookingStateTransition",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "from_state",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("requested", "Requested"),
                            ("accepted", "Accepted"),
                            ("paid", "Paid"),
                            ("picked_up", "Picked up"),
                            ("returned", "Returned"),
                            ("completed", "Completed"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                            ("disputed", "Disputed"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "to_state",
                    models.CharField(
                        choices=[
                            ("requested", "Requested"),
                            ("accepted", "Accepted"),
                            ("paid", "Paid"),
                            ("picked_up", "Picked up"),
                            ("returned", "Returned"),
                            ("completed", "Completed"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                            ("disputed", "Disputed"),
                        ],
                        max_length=20,
                    ),
                ),
                ("reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="booking_actions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transitions",
                        to="bookings.booking",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=ExclusionConstraint(
                name="booking_no_overlap",
                expressions=[
                    ("listing", RangeOperators.EQUAL),
                    (
                        TsTzRange(
                            F("start_at"),
                            F("end_at"),
                            RangeBoundary(
                                inclusive_lower=True, inclusive_upper=False
                            ),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(
                    state__in=[
                        "requested",
                        "accepted",
                        "paid",
                        "picked_up",
                    ]
                ),
            ),
        ),
    ]
