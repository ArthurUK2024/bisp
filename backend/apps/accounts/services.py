"""Services layer for the accounts app.

Every piece of non-CRUD business logic for auth / profile lives here and
gets called by the view layer. Views stay thin — the service owns the
domain rules and the tests.

PROF-02 avatar pipeline:

    1. Size check — reject > 2 MB (MAX_AVATAR_BYTES)
    2. Content-type sniff via python-magic (not filename extension) —
       accept only image/jpeg, image/png, image/webp. Catches the
       classic "virus.exe renamed to avatar.jpg" bypass that a
       filename-extension check would miss.
    3. Pillow open + verify — catches corrupt files and the
       decompression-bomb attack
    4. Re-open (verify consumes the file pointer), convert to RGB,
       thumbnail to fit inside 256x256 preserving aspect ratio
    5. Save as JPEG quality=85 to an in-memory buffer
    6. Write the buffer to profile.avatar via ImageField.save()
"""

from __future__ import annotations

import io
from typing import Final

import magic
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from .models import Profile

MAX_AVATAR_BYTES: Final[int] = 2 * 1024 * 1024  # 2 MB — mirrors PROF-02
AVATAR_TARGET: Final[tuple[int, int]] = (256, 256)
ALLOWED_MIMES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/webp"},
)


def save_avatar(profile: Profile, uploaded_file: UploadedFile) -> Profile:
    """Validate and re-save an avatar upload onto the profile.

    Raises rest_framework.exceptions.ValidationError on any failure so the
    view layer can return a clean 400 without a wrapping try/except.
    Returns the updated Profile on success.
    """
    # 1. Size check — reject before burning CPU on magic / Pillow.
    size = uploaded_file.size or 0
    if size > MAX_AVATAR_BYTES:
        raise ValidationError({"avatar": ["Avatar must be at most 2 MB."]})

    # 2. Content-type sniff — read the first 2 KB, sniff, then rewind.
    uploaded_file.seek(0)
    head = uploaded_file.read(2048)
    uploaded_file.seek(0)
    try:
        detected = magic.from_buffer(head, mime=True)
    except Exception as exc:  # noqa: BLE001 — libmagic errors are opaque
        raise ValidationError(
            {"avatar": ["Unsupported image type."]},
        ) from exc
    if detected not in ALLOWED_MIMES:
        raise ValidationError({"avatar": ["Unsupported image type."]})

    # 3. Pillow verify — catches corrupt files and decompression bombs.
    try:
        probe = Image.open(uploaded_file)
        probe.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError(
            {"avatar": ["File is not a readable image."]},
        ) from exc
    uploaded_file.seek(0)

    # 4. Re-open for the actual transform — verify() consumed the pointer
    # and the Image object it returned is no longer usable.
    image = Image.open(uploaded_file)
    image = image.convert("RGB")  # drop alpha; JPEG does not carry one
    image.thumbnail(AVATAR_TARGET)  # in-place, preserves aspect ratio

    # 5. Save as JPEG to a buffer.
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)

    # 6. Persist via the ImageField. upload_to='avatars/%Y/%m/' handles
    # the directory layout; save=True writes the Profile row back to the
    # DB so the caller can immediately read profile.avatar.url.
    profile.avatar.save(
        name=f"{profile.user_id}.jpg",
        content=ContentFile(buf.read()),
        save=True,
    )
    return profile
