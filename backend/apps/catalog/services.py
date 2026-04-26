"""Photo upload helper for listings.

Pipeline mirrors the avatar service in apps.accounts.services:

    1. Per-listing count cap (max 8 photos)
    2. Size check (5 MB)
    3. Content-type sniff via python-magic — defends against the
       "virus.exe renamed to thing.jpg" extension-spoof bypass
    4. Pillow open + verify — catches corrupt files and decompression bombs
    5. Re-open, convert to RGB, resize to fit inside 1600x1600 preserving
       aspect ratio
    6. Save as JPEG quality=85 to an in-memory buffer
    7. Persist via ImageField.save with a deterministic filename
"""

from __future__ import annotations

import io
from typing import Final

import magic
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from .models import ListingPhoto

MAX_PHOTO_BYTES: Final[int] = 5 * 1024 * 1024  # 5 MB
MAX_PHOTOS: Final[int] = 8
PHOTO_TARGET: Final[tuple[int, int]] = (1600, 1600)
ALLOWED_MIMES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/webp"},
)


def save_listing_photo(listing, uploaded_file):
    """Validate, resize, and persist a listing photo."""

    if listing.photos.count() >= MAX_PHOTOS:
        raise ValidationError({"photo": [f"Max {MAX_PHOTOS} photos per listing."]})

    if (uploaded_file.size or 0) > MAX_PHOTO_BYTES:
        raise ValidationError({"photo": ["Photo must be under 5 MB."]})

    uploaded_file.seek(0)
    head = uploaded_file.read(2048)
    uploaded_file.seek(0)
    try:
        detected = magic.from_buffer(head, mime=True)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError({"photo": ["Unsupported image type."]}) from exc
    if detected not in ALLOWED_MIMES:
        raise ValidationError({"photo": ["Unsupported image type."]})

    try:
        probe = Image.open(uploaded_file)
        probe.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError({"photo": ["File is not a readable image."]}) from exc
    uploaded_file.seek(0)

    image = Image.open(uploaded_file)
    image = image.convert("RGB")
    image.thumbnail(PHOTO_TARGET)

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)

    sort_order = listing.photos.count()
    photo = ListingPhoto(listing=listing, sort_order=sort_order)
    photo.image.save(
        name=f"{listing.id}-{sort_order}.jpg",
        content=ContentFile(buf.read()),
        save=False,
    )
    photo.save()
    return photo
