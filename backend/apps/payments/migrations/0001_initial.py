"""Initial payments schema (Phase 6)."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("bookings", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StripeEvent",
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
                ("event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(max_length=128)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("payload", models.JSONField()),
            ],
            options={"ordering": ["-received_at"]},
        ),
        migrations.CreateModel(
            name="Payment",
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
                ("stripe_intent_id", models.CharField(max_length=255, unique=True)),
                ("amount_cents", models.PositiveIntegerField()),
                ("currency", models.CharField(default="usd", max_length=3)),
                ("status", models.CharField(default="created", max_length=32)),
                ("client_secret", models.CharField(blank=True, max_length=512)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "booking",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="bookings.booking",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["booking", "status"], name="payments_pa_booking_45e2ec_idx"
            ),
        ),
    ]
