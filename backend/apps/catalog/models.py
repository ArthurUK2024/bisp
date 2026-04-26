"""Catalog models.

Listing: the rental item owners publish. One row per item, with an owner
FK back to accounts.User, three optional pricing columns (hour / day /
month, at least one required), a flat category and district enum, and a
soft-delete flag so deactivated listings survive for historical booking
integrity without appearing in the browse feed.

ListingPhoto: many photos per listing with a sort order that drives the
gallery. Uploads pass through save_listing_photo in services.py which
applies the same Pillow + python-magic pipeline as the avatar upload
from 02-03.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models


class Category(models.TextChoices):
    TOOLS = "tools", "Tools"
    ELECTRONICS = "electronics", "Electronics"
    EVENT_GEAR = "event_gear", "Event gear"
    SPORTS = "sports", "Sports"
    FURNITURE = "furniture", "Furniture"
    VEHICLES = "vehicles", "Vehicles"
    OTHER = "other", "Other"


class District(models.TextChoices):
    BEKTEMIR = "bektemir", "Bektemir"
    CHILONZOR = "chilonzor", "Chilonzor"
    MIROBOD = "mirobod", "Mirobod"
    MIRZO_ULUGBEK = "mirzo_ulugbek", "Mirzo Ulugbek"
    OLMAZOR = "olmazor", "Olmazor"
    SERGELI = "sergeli", "Sergeli"
    SHAYKHONTOHUR = "shaykhontohur", "Shaykhontohur"
    UCHTEPA = "uchtepa", "Uchtepa"
    YAKKASARAY = "yakkasaray", "Yakkasaray"
    YASHNABAD = "yashnabad", "Yashnabad"
    YUNUSOBOD = "yunusobod", "Yunusobod"
    YANGIHAYOT = "yangihayot", "Yangihayot"


class Listing(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
    )
    title = models.CharField(
        max_length=80,
        validators=[MinLengthValidator(3)],
    )
    description = models.TextField(max_length=2000)
    category = models.CharField(max_length=20, choices=Category.choices)
    district = models.CharField(max_length=30, choices=District.choices)

    price_hour = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_day = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_month = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # SRCH-04: persistent search vector kept fresh by signals.post_save.
    # Queried via SearchQuery + SearchRank in views.py.
    search_vector = SearchVectorField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["district", "is_active"]),
            GinIndex(fields=["search_vector"], name="catalog_search_vector_gin"),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.owner_id})"

    def clean(self) -> None:
        if not any([self.price_hour, self.price_day, self.price_month]):
            raise ValidationError(
                "At least one of price_hour, price_day, or price_month is required."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


def listing_photo_upload_to(instance: ListingPhoto, filename: str) -> str:
    return f"listings/{instance.listing_id}/{filename}"


class ListingPhoto(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=listing_photo_upload_to)
    sort_order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "uploaded_at"]

    def __str__(self) -> str:
        return f"Photo #{self.pk} for listing {self.listing_id}"
