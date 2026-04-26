"""Accounts views — Phase 2 Wave 1 auth contract.

Five views covering register, login (cookie-issuing), refresh (cookie-reading
+ rotating), logout (cookie-blacklisting), and /me/.

The cookie attributes are the single source of truth — if 02-04's Nuxt BFF
needs to change them, the change lands here first and the tests document
the move.

Cookie posture:
    httponly : always True — the browser JS layer must never touch the
               refresh token; access tokens live in memory only.
    secure   : True when ``DEBUG`` is False (production / staging over
               HTTPS); False when ``DEBUG`` is True so the local
               ``http://localhost`` dev loop can still receive the cookie.
               The ``Secure`` cookie attribute is otherwise ignored by the
               browser over plain HTTP.
    samesite : 'Lax' — cross-site top-level navigations still get the
               cookie, which the Nuxt BFF relies on when proxying. Strict
               would break the redirect-after-login flow.
    path     : /api/v1/auth/ — scopes the cookie to this app's routes so
               the rest of the API never receives it. 02-04's BFF mirrors
               this scoping on the browser side under /api/auth/.
    max_age  : seconds of SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].
"""

import contextlib

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Profile
from .serializers import (
    AvatarUploadSerializer,
    ProfileSerializer,
    PublicProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from .services import save_avatar

User = get_user_model()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"


def _refresh_cookie_secure() -> bool:
    """Production posture when DEBUG is off, dev posture when DEBUG is on."""
    return not settings.DEBUG


def _set_refresh_cookie(response: Response, refresh_value: str) -> None:
    """Single source of truth for cookie attributes. Mirrored by 02-04's BFF."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_value,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=_refresh_cookie_secure(),
        samesite="Lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
    )


class RegisterView(generics.CreateAPIView):
    """AUTH-01 — create user with validated email and password."""

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []


class LoginView(TokenObtainPairView):
    """AUTH-02 — issue access in body, refresh in HttpOnly cookie."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            return response
        refresh_value = response.data.pop("refresh", None)
        if refresh_value:
            _set_refresh_cookie(response, refresh_value)
        return response


class RefreshView(TokenRefreshView):
    """AUTH-02/03 — read cookie, issue new access, rotate cookie."""

    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def post(self, request, *args, **kwargs):
        cookie_value = request.COOKIES.get(REFRESH_COOKIE_NAME)
        body_value = request.data.get("refresh") if hasattr(request.data, "get") else None
        if not cookie_value and not body_value:
            # No refresh cookie and no refresh in body: the caller is
            # unauthenticated. SimpleJWT's serializer would return 400
            # ("this field is required"); 401 is the right status because
            # this endpoint's contract is "trade a refresh for an access"
            # and the refresh is missing, not malformed.
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if cookie_value and not body_value:
            # Inject cookie into a mutable copy of request.data so the parent
            # TokenRefreshSerializer.validate() finds it. ``_full_data`` is
            # the sanctioned (documented in DRF issue #5216) hook for
            # refresh-via-cookie patterns.
            data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
            data["refresh"] = cookie_value
            request._full_data = data  # noqa: SLF001
        response = super().post(request, *args, **kwargs)
        if response.status_code != 200:
            return response
        rotated_refresh = response.data.pop("refresh", None)
        if rotated_refresh:
            _set_refresh_cookie(response, rotated_refresh)
        return response


class LogoutView(APIView):
    """AUTH-04 — blacklist the current refresh, clear cookie, 204."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        cookie_value = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if cookie_value:
            # Token already blacklisted or invalid — still clear the cookie.
            with contextlib.suppress(TokenError):
                RefreshToken(cookie_value).blacklist()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class MeView(generics.RetrieveAPIView):
    """AUTH-06 supporting — the authenticated user's own shape."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class MyProfileView(generics.RetrieveUpdateAPIView):
    """PROF-01 — the authenticated user's own profile.

    GET returns the current shape; PATCH updates display_name / phone /
    bio (avatar is read-only on this endpoint — use AvatarUploadView).
    The signal in apps/accounts/signals.py guarantees request.user.profile
    always resolves, so there is no get_or_create dance here.
    """

    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self) -> Profile:
        return self.request.user.profile


class AvatarUploadView(APIView):
    """PROF-02 — multipart avatar upload delegated to save_avatar.

    The view is a thin wrapper: DRF's ImageField catches filename-
    extension mismatches and obvious non-images, then save_avatar takes
    over for size + python-magic sniff + Pillow resize + JPEG re-save.
    On success the updated profile shape is returned so the frontend
    can immediately render the new avatar URL without a follow-up GET.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_avatar(request.user.profile, serializer.validated_data["avatar"])
        return Response(
            ProfileSerializer(request.user.profile).data,
            status=status.HTTP_200_OK,
        )


class PublicProfileView(generics.RetrieveAPIView):
    """PROF-04 backend half — public-safe user+profile shape.

    AllowAny + no authentication_classes so anonymous callers can read
    the public page. Inactive users are filtered out at the queryset
    level so a deactivated account becomes a 404, not a 200 with an
    empty display_name. select_related('profile') keeps the lookup to
    a single SQL join so the serializer's source='profile.*' fields
    do not cause N+1 queries.
    """

    serializer_class = PublicProfileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    queryset = User.objects.filter(is_active=True).select_related("profile")
    lookup_field = "id"
