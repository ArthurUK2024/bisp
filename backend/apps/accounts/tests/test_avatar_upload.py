"""PROF-02 — avatar upload tests.

Covers the full avatar pipeline: size cap, python-magic content-type sniff,
Pillow resize to 256x256, JPEG re-save regardless of input format.

Two tests exercise the save_avatar service DIRECTLY instead of going through
the HTTP layer:

- test_save_avatar_service_rejects_text_disguised_as_jpeg: DRF's ImageField
  validator catches a plain-text file named virus.jpg before save_avatar
  ever runs, so the end-to-end test proves "something" rejects it but
  doesn't prove python-magic specifically is wired. Calling save_avatar
  directly with a SimpleUploadedFile exercises the magic.from_buffer
  branch.
- test_save_avatar_service_rejects_oversize: uses os.urandom pixel data
  so the JPEG encoder cannot compress it away — a 2500x2500 solid-colour
  JPEG is ~100 KB regardless of dimensions, so a size-based test needs
  high-entropy input bytes to reliably exceed 2 MB.
"""

import io
import os

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.exceptions import ValidationError

from apps.accounts.services import MAX_AVATAR_BYTES, save_avatar

pytestmark = pytest.mark.django_db


def _make_image(fmt: str, size=(400, 600), colour=(200, 100, 50)) -> bytes:
    """Build a small solid-colour image in the requested format."""
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format=fmt)
    return buf.getvalue()


def _make_noisy_jpeg(size: tuple[int, int]) -> bytes:
    """Build a JPEG with random pixel data so the encoder cannot compress it.

    Used by the oversize test: a 4000x4000 solid-colour JPEG compresses to
    ~100 KB, which is nowhere near the 2 MB cap. Random pixel data is
    high-entropy and produces a 3+ MB output at these dimensions.
    """
    width, height = size
    noise = os.urandom(width * height * 3)
    image = Image.frombytes("RGB", size, noise)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=100)
    return buf.getvalue()


# ----- HTTP-level tests --------------------------------------------------


def test_avatar_upload_requires_auth(api_client):
    response = api_client.post(reverse("my-avatar"))
    assert response.status_code == 401


def test_avatar_resized_to_256(authed_client_factory):
    client, user = authed_client_factory()
    upload = SimpleUploadedFile(
        "input.jpg",
        _make_image("JPEG"),
        content_type="image/jpeg",
    )
    response = client.post(
        reverse("my-avatar"),
        {"avatar": upload},
        format="multipart",
    )
    assert response.status_code == 200
    user.profile.refresh_from_db()
    with Image.open(user.profile.avatar.path) as saved:
        assert saved.size[0] <= 256
        assert saved.size[1] <= 256


def test_avatar_returns_updated_profile_shape(authed_client_factory):
    client, _ = authed_client_factory()
    upload = SimpleUploadedFile(
        "input.jpg",
        _make_image("JPEG"),
        content_type="image/jpeg",
    )
    response = client.post(
        reverse("my-avatar"),
        {"avatar": upload},
        format="multipart",
    )
    assert response.status_code == 200
    assert set(response.data.keys()) == {"display_name", "phone", "bio", "avatar"}
    assert response.data["avatar"] is not None


@pytest.mark.parametrize(
    "fmt,content_type",
    [
        ("JPEG", "image/jpeg"),
        ("PNG", "image/png"),
        ("WEBP", "image/webp"),
    ],
)
def test_avatar_accepts_jpeg_png_webp(authed_client_factory, fmt, content_type):
    client, _ = authed_client_factory()
    upload = SimpleUploadedFile(
        f"in.{fmt.lower()}",
        _make_image(fmt),
        content_type=content_type,
    )
    response = client.post(
        reverse("my-avatar"),
        {"avatar": upload},
        format="multipart",
    )
    assert response.status_code == 200


def test_avatar_saved_as_jpeg_regardless_of_input_format(authed_client_factory):
    client, user = authed_client_factory()
    upload = SimpleUploadedFile(
        "in.png",
        _make_image("PNG"),
        content_type="image/png",
    )
    response = client.post(
        reverse("my-avatar"),
        {"avatar": upload},
        format="multipart",
    )
    assert response.status_code == 200
    user.profile.refresh_from_db()
    with Image.open(user.profile.avatar.path) as saved:
        assert saved.format == "JPEG"


def test_avatar_http_rejects_non_image(authed_client_factory):
    """DRF's ImageField catches text-as-JPEG before the service runs.

    This test proves the HTTP pipeline returns 400 — it does NOT prove the
    python-magic branch. That proof lives in
    test_save_avatar_service_rejects_text_disguised_as_jpeg below.
    """
    client, _ = authed_client_factory()
    upload = SimpleUploadedFile(
        "virus.jpg",
        b"this is plain text, not an image",
        content_type="image/jpeg",
    )
    response = client.post(
        reverse("my-avatar"),
        {"avatar": upload},
        format="multipart",
    )
    assert response.status_code == 400


# ----- Service-level tests (SF-2 + SF-3) --------------------------------


def test_save_avatar_service_rejects_text_disguised_as_jpeg(user_factory):
    """SF-2: call save_avatar directly to exercise the python-magic branch.

    Serializer-level ImageField validation would intercept this payload
    before the service ever runs, so the service-level branch is only
    reachable via a direct call with a SimpleUploadedFile whose content
    is text.
    """
    user = user_factory()
    upload = SimpleUploadedFile(
        "virus.jpg",
        b"this is plain text, not an image",
        content_type="image/jpeg",
    )
    with pytest.raises(ValidationError) as exc:
        save_avatar(user.profile, upload)
    # Error shape: {'avatar': ['Unsupported image type.']}
    assert "avatar" in exc.value.detail


def test_save_avatar_service_rejects_oversize(user_factory):
    """SF-3: high-entropy pixel data to reliably exceed the 2 MB cap."""
    user = user_factory()
    big = _make_noisy_jpeg((2500, 2500))
    # Sanity check — prove the noise strategy works before asserting on the
    # service's behaviour. If the JPEG encoder ever starts compressing
    # random noise more aggressively, this line fails loudly before the
    # test regresses silently.
    assert len(big) > MAX_AVATAR_BYTES, (
        f"noisy JPEG was {len(big)} bytes, need > {MAX_AVATAR_BYTES}"
    )
    upload = SimpleUploadedFile(
        "big.jpg",
        big,
        content_type="image/jpeg",
    )
    with pytest.raises(ValidationError) as exc:
        save_avatar(user.profile, upload)
    assert "avatar" in exc.value.detail
