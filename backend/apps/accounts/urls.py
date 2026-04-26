"""Accounts URL routes — Phase 2 Waves 1 and 2.

Routes are mounted under ``/api/v1/`` by ``ijara/urls.py`` so the browser-
facing paths resolve to:

    Wave 1 (02-02 — auth):
        /api/v1/auth/register/   — RegisterView
        /api/v1/auth/login/      — LoginView   (SimpleJWT + HttpOnly cookie)
        /api/v1/auth/refresh/    — RefreshView (SimpleJWT + rotation)
        /api/v1/auth/logout/     — LogoutView  (blacklist + clear cookie)
        /api/v1/auth/me/         — MeView      (IsAuthenticated /me shape)

    Wave 2 (02-03 — profile):
        /api/v1/users/me/profile/   — MyProfileView      (GET/PATCH)
        /api/v1/users/me/avatar/    — AvatarUploadView   (POST multipart)
        /api/v1/users/<int:id>/     — PublicProfileView  (GET AllowAny)

Every route is named so ``reverse()`` works from the test suite and from
any future plan that composes against these endpoints.
"""

from django.urls import path

from .views import (
    AvatarUploadView,
    LoginView,
    LogoutView,
    MeView,
    MyProfileView,
    PublicProfileView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    # Wave 1 — auth
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/me/", MeView.as_view(), name="me"),
    # Wave 2 — profile
    path("users/me/profile/", MyProfileView.as_view(), name="my-profile"),
    path("users/me/avatar/", AvatarUploadView.as_view(), name="my-avatar"),
    path("users/<int:id>/", PublicProfileView.as_view(), name="public-profile"),
]
