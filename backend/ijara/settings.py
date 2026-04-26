"""Django settings for the Ijara project.

Single-file layout per CONTEXT.md. Every value is sourced from the environment
via django-environ. SECRET_KEY has no default and raises ImproperlyConfigured
at import time if DJANGO_SECRET_KEY is missing.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

# --- SECURITY ---------------------------------------------------------------
# SECRET_KEY has no default — missing env var raises at import time. This is
# the correct production behaviour; .env.example ships a dev value so the
# one-command demo still works on a fresh clone.
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "api"],
)

# --- APPLICATIONS -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    # Local
    "apps.common",
    "apps.accounts",
    "apps.catalog",
    "apps.bookings",
    "apps.payments",
    "apps.search",
]

# corsheaders.middleware.CorsMiddleware MUST sit above CommonMiddleware for the
# CORS headers to land on the response.
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ijara.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ijara.wsgi.application"
ASGI_APPLICATION = "ijara.asgi.application"

# --- DATABASE ---------------------------------------------------------------
# django-environ parses DATABASE_URL. In tests the default can be overridden
# via pytest-django by setting DATABASE_URL=sqlite:///:memory: in the env.
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3"),
}
# Wrap every request in a transaction. Phase 2 booking service and profile
# avatar upload both rely on SELECT FOR UPDATE semantics, so the default
# auto-commit behaviour has to flip to request-scoped atomicity before any
# write view lands.
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# --- CUSTOM USER MODEL ------------------------------------------------------
# CRITICAL: set BEFORE any `migrate` runs. The matching initial migration
# lives at apps/accounts/migrations/0001_initial.py and is committed together
# with this setting, so the first `migrate` never creates auth_user.
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.LetterAndDigitValidator"},
]

# --- INTERNATIONALISATION ---------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"  # Postgres stores UTC; Nuxt displays Asia/Tashkent.
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Absolute origin the browser can reach Django at. Serializers prepend
# this to image URLs so a photo link stays valid whether the JSON was
# produced during SSR (when the request Host is api:8000) or a direct
# browser call (localhost:8000).
MEDIA_HOST = env("DJANGO_MEDIA_HOST", default="http://localhost:8000")

# Avatar cap in PROF-02 is 2 MB. The upload and data limits are set to
# 2_621_440 bytes (2.5 MB) — a 500 KB margin over the 2 MB cap so the
# serializer's own size check returns a clean 400 before Django's middleware
# short-circuits with a raw 413. Raising this beyond 2.5 MB opens the door
# to memory-resident MB-scale multipart bodies and is out of scope for v1.
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- REST FRAMEWORK ---------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# --- SIMPLE JWT -------------------------------------------------------------
# Locked for Phase 2: five-minute access, seven-day refresh, rotate-on-refresh
# with blacklist-after-rotation so a stolen refresh token cannot outlive a
# legitimate rotation. Any drift here breaks Plan 02-02 and Plan 02-04 —
# test_jwt_config.py pins every value below.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Ijara API",
    "DESCRIPTION": "Peer-to-peer rental marketplace for Tashkent.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- CORS / CSRF ------------------------------------------------------------
# Explicit whitelist. Never wildcard. See PITFALLS.md #7 (the wildcard origins
# trap). Phase 2+ can extend the list via the DJANGO_CORS_ALLOWED_ORIGINS env var.
CORS_ALLOWED_ORIGINS = env.list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000"],
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:3000"],
)
# Do not enable the wildcard origins flag anywhere in committed code.

# --- STRIPE -----------------------------------------------------------------
# Phase 6 Stripe wiring. STRIPE_SECRET_KEY is a sk_test_... key in dev. The
# webhook secret comes from `stripe listen --forward-to ...` output. When
# either is the placeholder string the payments app rejects calls with a
# friendly 503 instead of trying to talk to Stripe.
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_PUBLISHABLE_KEY = env("NUXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", default="")


def stripe_configured() -> bool:
    """True when both keys look like real Stripe keys, not the placeholders."""
    return (
        STRIPE_SECRET_KEY.startswith("sk_")
        and STRIPE_WEBHOOK_SECRET.startswith("whsec_")
        and "replace_me" not in STRIPE_SECRET_KEY
    )


# --- OPENAI -----------------------------------------------------------------
# Used by /api/v1/listings/ai-suggest/ to turn uploaded photos into a draft
# title/description/category/price tier. Empty key means the endpoint
# returns 503 and the front end gracefully falls back to manual entry.
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")


def openai_configured() -> bool:
    return OPENAI_API_KEY.startswith("sk-")
