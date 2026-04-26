"""Photo upload helper and AI suggestion helper for listings.

The photo pipeline mirrors the avatar service in apps.accounts.services:

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

import base64
import io
import json
import logging
from typing import Final

import magic
from django.conf import settings
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


# ---------------------------------------------------------------------------
# AI suggestion: photo -> draft listing fields
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

AI_INPUT_TARGET: Final[tuple[int, int]] = (768, 768)
AI_MAX_PHOTOS: Final[int] = 4

_VALID_CATEGORIES = {
    "tools",
    "electronics",
    "event_gear",
    "sports",
    "furniture",
    "vehicles",
    "other",
}

AI_SYSTEM_PROMPT = (
    "You are a listing assistant for a peer-to-peer rental marketplace in "
    "Tashkent, Uzbekistan. The user is renting out an item and has uploaded "
    "one or more photos of it. Look at the photos and produce a draft "
    "listing. Pricing is in Uzbek so'm (UZS). Day rates for typical items "
    "fall between 30000 and 300000 UZS, vehicles between 400000 and 800000 "
    "UZS per day. Hour rates only make sense for short-use items like a "
    "scooter or a camera. Month rates only make sense for high-value items "
    "like vehicles or pro cameras. Always set at least one price tier; "
    "leave the rest as null when they do not apply. Keep the title under "
    "80 characters. Keep the description between two and four sentences "
    "and under 600 characters. Pick the single best-fitting category from "
    "the allowed list. Never invent details you cannot see in the photo."
)


def _encode_photo_for_vision(uploaded_file) -> str:
    """Validate, downscale, and base64-encode an upload for the vision API."""
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

    image = Image.open(uploaded_file).convert("RGB")
    image.thumbnail(AI_INPUT_TARGET)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=78, optimize=True)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _coerce_int_or_none(value):
    if value is None:
        return None
    try:
        n = int(round(float(value)))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _normalise_suggestion(raw: dict) -> dict:
    """Strip unknown fields and clamp values into the contract the form expects."""
    title = (raw.get("title") or "").strip()[:80]
    description = (raw.get("description") or "").strip()[:600]
    category = raw.get("category")
    if category not in _VALID_CATEGORIES:
        category = None
    return {
        "title": title or None,
        "description": description or None,
        "category": category,
        "price_hour": _coerce_int_or_none(raw.get("price_hour")),
        "price_day": _coerce_int_or_none(raw.get("price_day")),
        "price_month": _coerce_int_or_none(raw.get("price_month")),
    }


def suggest_listing_from_photos(uploaded_files) -> dict:
    """Send up to AI_MAX_PHOTOS images to OpenAI and return a normalised draft.

    Raises ValidationError on bad input. Returns a dict with keys:
        title, description, category, price_hour, price_day, price_month
    Any field may be None — the caller pre-fills only the truthy ones.
    """
    if not uploaded_files:
        raise ValidationError({"photos": ["At least one photo is required."]})

    if not settings.OPENAI_API_KEY:
        # Caller turns this into a 503 — front end falls back to manual entry.
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    payload_images = [_encode_photo_for_vision(f) for f in uploaded_files[:AI_MAX_PHOTOS]]

    # Lazy import so the dependency is only required when the feature is on.
    from openai import OpenAI  # type: ignore[import-not-found]

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                "Look at these photos and return a JSON object with: "
                "title, description, category (one of: tools, electronics, "
                "event_gear, sports, furniture, vehicles, other), "
                "price_hour (UZS, integer or null), price_day (UZS, integer "
                "or null), price_month (UZS, integer or null). "
                "Return JSON only, no extra text."
            ),
        }
    ]
    for data_url in payload_images:
        user_content.append({"type": "image_url", "image_url": {"url": data_url, "detail": "low"}})

    # Lazy import the error classes so the dependency stays optional.
    from openai import (  # type: ignore[import-not-found]
        APIConnectionError,
        APIError,
        AuthenticationError,
        RateLimitError,
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            max_tokens=600,
            temperature=0.4,
        )
    except (RateLimitError, AuthenticationError, APIConnectionError, APIError) as exc:
        logger.warning("OpenAI listing-suggest call failed: %s", exc)
        # Surface as RuntimeError so the view turns it into a 503 and the
        # front end shows the manual-entry fallback banner instead of a 500.
        raise RuntimeError("OpenAI request failed") from exc

    text = (response.choices[0].message.content or "").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("OpenAI returned non-JSON content: %r", text[:200])
        return _normalise_suggestion({})

    return _normalise_suggestion(parsed)
