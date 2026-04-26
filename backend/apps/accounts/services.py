from __future__ import annotations

import io
from typing import Final

import magic
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from .models import Profile

MAX_AVATAR_BYTES: Final[int] = 2 * 1024 * 1024
AVATAR_TARGET: Final[tuple[int, int]] = (256, 256)
ALLOWED_MIMES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/webp"},
)


def save_avatar(profile: Profile, uploaded_file: UploadedFile) -> Profile:
    size = uploaded_file.size or 0
    if size > MAX_AVATAR_BYTES:
        raise ValidationError({"avatar": ["Avatar must be at most 2 MB."]})

    uploaded_file.seek(0)
    head = uploaded_file.read(2048)
    uploaded_file.seek(0)
    try:
        detected = magic.from_buffer(head, mime=True)
    except Exception as exc:  # noqa: BLE001
        raise ValidationError({"avatar": ["Unsupported image type."]}) from exc
    if detected not in ALLOWED_MIMES:
        raise ValidationError({"avatar": ["Unsupported image type."]})

    try:
        probe = Image.open(uploaded_file)
        probe.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError({"avatar": ["File is not a readable image."]}) from exc
    uploaded_file.seek(0)

    image = Image.open(uploaded_file)
    image = image.convert("RGB")
    image.thumbnail(AVATAR_TARGET)

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)

    profile.avatar.save(
        name=f"{profile.user_id}.jpg",
        content=ContentFile(buf.read()),
        save=True,
    )
    return profile
