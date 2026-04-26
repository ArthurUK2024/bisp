FROM python:3.12-slim-bookworm

ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Runtime deps: curl (compose healthcheck), libpq5 (psycopg), libmagic1
# (python-magic shared C library for PROF-02 avatar content-type sniffing),
# build tools for wheels.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      curl \
      libpq5 \
      libpq-dev \
      libmagic1 \
      build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install uv (Astral) — the Python package manager used on cold Docker builds.
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy lockfile inputs first for better layer caching.
COPY pyproject.toml uv.lock* ./

# Export the locked dependency set (including the dev group — pytest runs
# inside the image during Phase 1 verification) and install it system-wide
# so every tool is on PATH without a venv activation dance. Fallback: plain
# pip install if uv cannot resolve the lockfile.
RUN (uv export --frozen --no-emit-project --format requirements-txt \
       > /tmp/requirements.txt \
     && uv pip install --system --no-cache -r /tmp/requirements.txt \
     && rm /tmp/requirements.txt) \
    || (pip install --no-cache-dir \
          "Django>=5.2,<5.3" "djangorestframework>=3.16,<3.17" \
          "psycopg[binary]>=3.2,<3.3" "django-environ>=0.12,<0.13" \
          "django-cors-headers>=4.7,<5" "django-filter>=25,<26" \
          "drf-spectacular>=0.28,<0.29" \
          "djangorestframework-simplejwt>=5.5,<5.6" "Pillow>=11,<12" \
          "python-magic>=0.4,<0.5" \
          "stripe>=10,<13" "openai>=1.50,<2" \
          "pytest>=8,<9" "pytest-django>=4.9,<5" "ruff>=0.9,<1.0" \
          "factory-boy>=3,<4")

# Copy the rest of the source tree.
COPY . /app

# The entrypoint must be executable — without this line the container errors
# on start with permission denied.
RUN chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000

CMD ["/app/scripts/entrypoint.sh"]
