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
    return not settings.DEBUG


def _set_refresh_cookie(response: Response, refresh_value: str) -> None:
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
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []


class LoginView(TokenObtainPairView):
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
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def post(self, request, *args, **kwargs):
        cookie_value = request.COOKIES.get(REFRESH_COOKIE_NAME)
        body_value = request.data.get("refresh") if hasattr(request.data, "get") else None
        if not cookie_value and not body_value:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if cookie_value and not body_value:
            # Inject the cookie into request.data so TokenRefreshSerializer.validate finds it.
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
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        cookie_value = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if cookie_value:
            with contextlib.suppress(TokenError):
                RefreshToken(cookie_value).blacklist()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class MyProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self) -> Profile:
        return self.request.user.profile


class AvatarUploadView(APIView):
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
    serializer_class = PublicProfileSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []
    queryset = User.objects.filter(is_active=True).select_related("profile")
    lookup_field = "id"
